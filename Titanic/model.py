import pandas as pd
import numpy as np
import os

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt

from sklearn import tree
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


# Open the Titanic dataset
df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'Titanic.csv'))


# Print the first few lines of the dataframe
#
# Check the names and types of each column
print(df.head())

# scikit-learn can't work with arbitrary strings, like "male" and "female"
# Create a new field that turns the "Sex" string into a binary number
df['Sex_numeric'] = np.where(df['Sex'] == 'male', 1, 0)


# Pull out the Pclass, Age, and Sex_numeric columns into their own dataframe
X = df[['Pclass', 'Age', 'Sex_numeric']]


# Extract the target variable
y = df.pop('Survived').values
print(y)

# Create the Decision TreeClassifier object
# max_depth=2 restricts the size of the tree to only two splits
clf = tree.DecisionTreeClassifier(max_depth=2)


# Fit the decision tree
# Our goal is to predict Survival based on Pclass, Age, and Sex
clf.fit(X, y) 

# Create the Decision TreeClassifier object
# max_depth=2 restricts the size of the tree to only two splits
clf = tree.DecisionTreeClassifier(max_depth=10)


# Fit the decision tree
# Our goal is to predict Survival based on Pclass, Age, and Sex
clf.fit(X, y) 

tree.export_graphviz(clf, out_file='tree.dot', feature_names=['Pclass', 'Age', 'Sex_numeric'],
                     class_names=['Did not survive', 'Survived'],  filled=True, rounded=True, special_characters=True,
                     proportion=True)