#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_iris

def relu(x):
    return np.maximum(0, x)

def relu_derivative(x):
    return (x > 0).astype(float)

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def predict(hidden_weights, output_weights, point):
    """Forward pass with ReLU hidden layer, sigmoid output."""
    hidden_inputs  = hidden_weights @ point            # (num_hidden,)
    hidden_outputs = relu(hidden_inputs)               # (num_hidden,)
    output = sigmoid(output_weights @ hidden_outputs)  # (3,)
    return output

def train(hidden_weights, output_weights, point, target_vec, learning_rate):
    """One backprop update using ReLU at the hidden layer."""
    point = np.array(point, dtype=float)

    # --- Forward pass ---
    hidden_inputs  = hidden_weights @ point            # (num_hidden,)
    hidden_outputs = relu(hidden_inputs)               # (num_hidden,)
    output = sigmoid(output_weights @ hidden_outputs)  # (3,)

    # --- Backpropagation ---
    # Output error signals (sigmoid derivative): shape (3,)
    output_error = (target_vec - output) * output * (1 - output)

    # Hidden error signals (ReLU derivative): shape (num_hidden,)
    # ReLU derivative: 1 where pre-activation > 0, else 0
    hidden_errors = (output_weights.T @ output_error) * relu_derivative(hidden_inputs)

    # --- Weight updates ---
    output_weights += learning_rate * np.outer(output_error, hidden_outputs)  # (3, num_hidden)
    hidden_weights += learning_rate * np.outer(hidden_errors, point)          # (num_hidden, num_inputs)

    return hidden_weights, output_weights

def epoch(hidden_weights, output_weights, training_set, training_labels, learning_rate):
    """One full pass over the training set in randomised order."""
    indices = np.random.permutation(len(training_set))
    for i in indices:
        hidden_weights, output_weights = train(
            hidden_weights, output_weights,
            training_set[i], training_labels[i], learning_rate
        )
    return hidden_weights, output_weights

def avg_error(hidden_weights, output_weights, dataset, labels):
    """Mean absolute error across the dataset."""
    total = 0.0
    for point, target_vec in zip(dataset, labels):
        output = predict(hidden_weights, output_weights, point)
        total += np.mean(np.abs(target_vec - output))
    return total / len(labels)

def evaluate(hidden_weights, output_weights, dataset, labels):
    """Classification accuracy: pick the output node with the highest value."""
    correct = 0
    for point, target_vec in zip(dataset, labels):
        output = predict(hidden_weights, output_weights, point)
        if np.argmax(output) == np.argmax(target_vec):
            correct += 1
    return correct / len(labels)


if __name__ == "__main__":
    np.random.seed(42)

    # --- Load & prepare iris dataset ---
    iris = load_iris()
    X = iris.data.astype(float)   # (150, 4)
    y = iris.target               # (150,) — values 0, 1, 2

    # Normalise each feature to [0, 1]
    X = (X - X.min(axis=0)) / (X.max(axis=0) - X.min(axis=0))

    # One-hot encode labels → (150, 3)
    Y = np.zeros((150, 3))
    for i, label in enumerate(y):
        Y[i, label] = 1

    # --- Train / test split: 30 test (20%), 120 train (80%) ---
    # Use the same seed so both versions get identical splits
    indices = np.random.permutation(150)
    test_idx  = indices[:30]
    train_idx = indices[30:]

    X_train, Y_train = X[train_idx], Y[train_idx]
    X_test,  Y_test  = X[test_idx],  Y[test_idx]

    # --- Network parameters ---
    num_inputs    = 4
    num_hidden    = 8
    num_outputs   = 3
    learning_rate = 0.1
    num_epochs    = 500

    hidden_weights = np.random.uniform(-1, 1, (num_hidden, num_inputs))
    output_weights = np.random.uniform(-1, 1, (num_outputs, num_hidden))

    # --- Training loop ---
    errors_relu = []
    for e in range(num_epochs):
        hidden_weights, output_weights = epoch(
            hidden_weights, output_weights, X_train, Y_train, learning_rate
        )
        err = avg_error(hidden_weights, output_weights, X_train, Y_train)
        errors_relu.append(err)
        if (e + 1) % 100 == 0:
            print(f"Epoch {e + 1:>4}: avg training error = {err:.4f}")

    # --- Final test evaluation ---
    accuracy = evaluate(hidden_weights, output_weights, X_test, Y_test)
    print(f"\nTest accuracy: {accuracy * 100:.1f}%  ({int(accuracy * 30)}/30 correct)")

    # --- Load sigmoid errors for comparison ---
    # Re-run sigmoid version with same seed to get its error curve
    np.random.seed(42)
    indices2    = np.random.permutation(150)
    X_train2    = X[indices2[30:]]
    Y_train2    = Y[indices2[30:]]

    hw2 = np.random.uniform(-1, 1, (num_hidden, num_inputs))
    ow2 = np.random.uniform(-1, 1, (num_outputs, num_hidden))

    def sigmoid_train(hw, ow, point, target_vec, lr):
        point = np.array(point, dtype=float)
        hi = hw @ point
        ho = sigmoid(hi)
        out = sigmoid(ow @ ho)
        oe = (target_vec - out) * out * (1 - out)
        he = (ow.T @ oe) * ho * (1 - ho)
        ow += lr * np.outer(oe, ho)
        hw += lr * np.outer(he, point)
        return hw, ow

    errors_sigmoid = []
    for e in range(num_epochs):
        idx = np.random.permutation(len(X_train2))
        for i in idx:
            hw2, ow2 = sigmoid_train(hw2, ow2, X_train2[i], Y_train2[i], learning_rate)
        total = sum(np.mean(np.abs(Y_train2[i] - sigmoid(ow2 @ sigmoid(hw2 @ X_train2[i]))))
                    for i in range(len(X_train2)))
        errors_sigmoid.append(total / len(X_train2))

    # --- Comparison plot ---
    plt.figure(figsize=(9, 5))
    plt.plot(range(1, num_epochs + 1), errors_sigmoid, label="Sigmoid hidden", linewidth=1.5)
    plt.plot(range(1, num_epochs + 1), errors_relu,    label="ReLU hidden",    linewidth=1.5)
    plt.xlabel("Epoch")
    plt.ylabel("Average Training Error")
    plt.title("Iris — Sigmoid vs ReLU Hidden Layer")
    plt.legend()
    plt.grid(True, alpha=0.4)
    plt.tight_layout()
    plt.savefig("Sprint6/iris_relu_vs_sigmoid.png", dpi=150)
    plt.show()
    print("Plot saved to Sprint6/iris_relu_vs_sigmoid.png")
