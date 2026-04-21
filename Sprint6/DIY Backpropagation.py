#!/usr/bin/env python3
import numpy as np

# XOR dataset
XOR_INPUTS  = [[0, 0], [0, 1], [1, 0], [1, 1]]
XOR_LABELS  = [0, 1, 1, 0]

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def predict(hidden_weights, output_weights, point):
    hidden_weights = np.array(hidden_weights)
    output_weights = np.array(output_weights)
    point = np.array(point)

    # Compute hidden layer activations
    hidden_inputs = hidden_weights @ point          # shape: (num_hidden_nodes,)
    hidden_outputs = sigmoid(hidden_inputs)         # shape: (num_hidden_nodes,)

    # Compute output layer activation
    output_input = output_weights @ hidden_outputs  # scalar
    output = sigmoid(output_input)                  # scalar

    return output

def train(hidden_weights, output_weights, point, target_label, learning_rate):
    hidden_weights = np.array(hidden_weights, dtype=float)
    output_weights = np.array(output_weights, dtype=float)
    point = np.array(point, dtype=float)

    # --- Forward pass ---
    hidden_inputs = hidden_weights @ point
    hidden_outputs = sigmoid(hidden_inputs)

    output_input = output_weights @ hidden_outputs
    output = sigmoid(output_input)

    # --- Backpropagation ---
    # Output layer error signal
    output_error = (target_label - output) * output * (1 - output)

    # Hidden layer error signals
    hidden_errors = (output_weights * output_error) * hidden_outputs * (1 - hidden_outputs)

    # --- Weight updates ---
    output_weights += learning_rate * output_error * hidden_outputs
    hidden_weights += learning_rate * np.outer(hidden_errors, point)

    return hidden_weights, output_weights

def epoch(hidden_weights, output_weights, training_set, training_labels, learning_rate):
    hidden_weights = np.array(hidden_weights, dtype=float)
    output_weights = np.array(output_weights, dtype=float)

    for point, label in zip(training_set, training_labels):
        hidden_weights, output_weights = train(
            hidden_weights, output_weights, point, label, learning_rate
        )

    return hidden_weights, output_weights

def evaluate(hidden_weights, output_weights, testing_set, testing_labels):
    correct = 0

    for point, label in zip(testing_set, testing_labels):
        output = predict(hidden_weights, output_weights, point)
        prediction = 1 if output >= 0.5 else 0
        if prediction == label:
            correct += 1

    return correct / len(testing_labels)


if __name__ == "__main__":
    np.random.seed(42)

    num_inputs  = 2
    num_hidden  = 4
    learning_rate = 0.5
    num_epochs  = 10000

    hidden_weights = np.random.uniform(-1, 1, (num_hidden, num_inputs))
    output_weights = np.random.uniform(-1, 1, (num_hidden,))

    for i in range(num_epochs):
        hidden_weights, output_weights = epoch(
            hidden_weights, output_weights,
            XOR_INPUTS, XOR_LABELS, learning_rate
        )

    accuracy = evaluate(hidden_weights, output_weights, XOR_INPUTS, XOR_LABELS)
    print(f"Accuracy after {num_epochs} epochs: {accuracy * 100:.1f}%")

    print("\nPredictions:")
    for point, label in zip(XOR_INPUTS, XOR_LABELS):
        out = predict(hidden_weights, output_weights, point)
        pred = 1 if out >= 0.5 else 0
        print(f"  {point} -> predicted {pred}  (expected {label}, raw={out:.4f})")