# -*- coding: utf-8 -*-
"""part3and4.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1RbLnd4FOtL4alkh6Z8Yu9gDsswEzKr93
"""

import os
import torch
import torch.optim as optim
import torch.nn as nn
from torchvision import transforms, datasets, models
from torchvision.io import read_image
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import pandas as pd
import time

from google.colab import drive
import os
drive.mount('/content/Mydrive')

img_dir = '/content/Mydrive/MyDrive/submission_files1/mhist_dataset/images'

# Set device to GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

"""// cross architecture mnist dataset"""

from networks import VGG11

# Custom Dataset class to load synthetic MNIST images
class SyntheticMNISTDataset(Dataset):
    def __init__(self, img_dir, transform=None):
        self.img_dir = img_dir
        self.transform = transform
        self.images = []
        self.labels = []

        # Load images and labels from the directory
        for img_name in os.listdir(img_dir):
            label = int(img_name.split('_')[1])  # Extract label from filename like 'class_1_image_8'
            img_path = os.path.join(img_dir, img_name)
            self.images.append(img_path)
            self.labels.append(label)

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img_path = self.images[idx]
        image = read_image(img_path).float() / 255.0  # Normalize pixel values
        label = self.labels[idx]

        if self.transform:
            image = self.transform(image)

        return image, label

# Define transformations for synthetic MNIST images
transform = transforms.Compose([
    transforms.Resize((28, 28)),
    transforms.Grayscale(),  # Convert to grayscale if not already
    transforms.Normalize((0.5,), (0.5,))  # Normalization for MNIST
])

# Load synthetic MNIST dataset
synthetic_mnist_dir = '/content/synthetic_images'  # Replace with your directory path
synthetic_mnist_dataset = SyntheticMNISTDataset(synthetic_mnist_dir, transform=transform)
synthetic_mnist_loader = DataLoader(synthetic_mnist_dataset, batch_size=10, shuffle=True)

# Load original MNIST test dataset
test_transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,))
])
mnist_test_dataset = datasets.MNIST(root='./data', train=False, transform=test_transform, download=True)
mnist_test_loader = DataLoader(mnist_test_dataset, batch_size=256, shuffle=False)

# Initialize VGG11 model
model = VGG11(channel=1, num_classes=10).to(device)

# Set up optimizer and loss function with a reduced learning rate
optimizer = optim.SGD(model.parameters(), lr=0.001, momentum=0.9)
criterion = nn.CrossEntropyLoss().to(device)

# Training VGG11 on synthetic dataset with 20 epochs
epochs = 20
for epoch in range(epochs):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    for images, labels in synthetic_mnist_loader:
        images, labels = images.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)

        loss.backward()
        optimizer.step()

        running_loss += loss.item() * labels.size(0)
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

    epoch_loss = running_loss / total
    epoch_accuracy = 100.0 * correct / total
    print(f"Epoch [{epoch+1}/{epochs}] - Loss: {epoch_loss:.4f}, Accuracy: {epoch_accuracy:.2f}%")

# Evaluate VGG11 on original MNIST test set
model.eval()
test_loss = 0.0
correct = 0
total = 0
with torch.no_grad():
    for images, labels in mnist_test_loader:
        images, labels = images.to(device), labels.to(device)
        outputs = model(images)
        loss = criterion(outputs, labels)

        test_loss += loss.item() * labels.size(0)
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

test_accuracy = 100.0 * correct / total
average_test_loss = test_loss / total
print(f"\nTest Loss on original MNIST test set: {average_test_loss:.4f}")
print(f"Test Accuracy on original MNIST test set: {test_accuracy:.2f}%")

# Define custom dataset class for synthetic MHIST images
class SyntheticMHISTDataset(Dataset):
    def __init__(self, img_dir, transform=None):
        self.img_dir = img_dir
        self.transform = transform
        self.images = []
        self.labels = []

        # Load images and labels from the directory
        for img_name in os.listdir(img_dir):
            label = int(img_name.split('_')[1])  # Extract label from filename like 'class_1_image_8'
            img_path = os.path.join(img_dir, img_name)
            self.images.append(img_path)
            self.labels.append(label)

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img_path = self.images[idx]
        image = Image.open(img_path).convert("RGB")
        label = self.labels[idx]

        if self.transform:
            image = self.transform(image)

        return image, label

# Define custom dataset class for real MHIST dataset
class RealMHISTDataset(Dataset):
    def __init__(self, img_dir, csv_file, transform=None):
        self.img_dir = img_dir
        self.annotations = pd.read_csv(csv_file)
        self.transform = transform
        self.label_map = {"HP": 0, "SSA": 1}

        self.images = []
        self.labels = []

        for idx, row in self.annotations.iterrows():
            img_name = row['Image Name']
            label_str = row['Majority Vote Label']
            if label_str in self.label_map:
                int_label = self.label_map[label_str]
                self.images.append(img_name)
                self.labels.append(int_label)

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img_path = os.path.join(self.img_dir, self.images[idx])
        image = Image.open(img_path).convert("RGB")
        label = self.labels[idx]

        if self.transform:
            image = self.transform(image)

        return image, label

# Data transformations (resizing to 224x224 to match PyTorch VGG11 input requirements)
transform_mhist = transforms.Compose([
    transforms.Resize((224, 224)),  # Resize to 224x224
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])  # Standard RGB normalization
])

# Load synthetic and real MHIST datasets
synthetic_mhist_dir = '/content/synthetic_mhist'  # Path to synthetic MHIST images
real_mhist_img_dir = '/content/gdrive/MyDrive/submission_files1/mhist_dataset/images'  # Path to real MHIST images on Google Drive
annotations_file = "/content/gdrive/MyDrive/submission_files1/mhist_dataset/annotations.csv"  # Path to annotations.csv for MHIST

synthetic_mhist_dataset = SyntheticMHISTDataset(synthetic_mhist_dir, transform=transform_mhist)
real_mhist_dataset = RealMHISTDataset(real_mhist_img_dir, annotations_file, transform=transform_mhist)

# Data loaders
batch_size_train = 10
batch_size_test = 256
synthetic_mhist_loader = DataLoader(synthetic_mhist_dataset, batch_size=batch_size_train, shuffle=True)
real_mhist_loader = DataLoader(real_mhist_dataset, batch_size=batch_size_test, shuffle=False)

# Load VGG11 from torchvision and modify the final layer
model = models.vgg11(pretrained=False)  # Use pretrained=True if you want to fine-tune from ImageNet weights
model.classifier[6] = nn.Linear(4096, 2)  # Change the output layer to match 2 classes
model = model.to(device)

# Training and evaluation function with timing
def train_and_evaluate(model, train_loader, test_loader, epochs=20, lr=0.001):
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    start_time = time.time()

    # Training loop
    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * images.size(0)

        epoch_loss = running_loss / len(train_loader.dataset)
        print(f"Epoch [{epoch+1}/{epochs}], Loss: {epoch_loss:.4f}")

    training_time = time.time() - start_time
    print(f"Training completed in {training_time:.2f} seconds")

    # Evaluation loop
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for images, labels in test_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    accuracy = 100 * correct / total
    print(f"Test Accuracy: {accuracy:.2f}%")
    return accuracy, training_time

# Train and evaluate the modified VGG11 model on synthetic MHIST and evaluate on real MHIST
print("Training on synthetic MHIST, evaluating on real MHIST:")
mhist_accuracy, mhist_training_time = train_and_evaluate(model, synthetic_mhist_loader, real_mhist_loader, epochs=20)
print(f"MHIST - Training Time: {mhist_training_time:.2f} seconds, Test Accuracy: {mhist_accuracy:.2f}%")

"""////4

//USE SYNTHETIC MNIST REAL AS A TEST
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import datasets, transforms
from PIL import Image

# Set device to GPU if available
device = 'cuda' if torch.cuda.is_available() else 'cpu'

# Define a basic CNN architecture template to allow simple NAS
class SimpleCNN(nn.Module):
    def __init__(self, num_channels, num_classes, num_conv_layers, num_filters):
        super(SimpleCNN, self).__init__()
        layers = []
        in_channels = num_channels

        # Add convolutional layers dynamically based on NAS config
        for _ in range(num_conv_layers):
            layers.append(nn.Conv2d(in_channels, num_filters, kernel_size=3, padding=1))
            layers.append(nn.ReLU(inplace=True))
            layers.append(nn.MaxPool2d(kernel_size=2, stride=2))
            in_channels = num_filters

        self.features = nn.Sequential(*layers)
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(num_filters * (28 // (2 ** num_conv_layers)) ** 2, 128),
            nn.ReLU(inplace=True),
            nn.Linear(128, num_classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

# Define synthetic MNIST dataset class
class SyntheticMNISTDataset(Dataset):
    def __init__(self, img_dir, transform=None):
        self.img_dir = img_dir
        self.transform = transform
        self.images = []
        self.labels = []

        # Load images and labels from the directory
        for img_name in os.listdir(img_dir):
            label = int(img_name.split('_')[1])  # Extract label from filename like 'class_1_image_8'
            img_path = os.path.join(img_dir, img_name)
            self.images.append(img_path)
            self.labels.append(label)

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img_path = self.images[idx]
        image = Image.open(img_path).convert("L")  # Convert to grayscale
        label = self.labels[idx]

        if self.transform:
            image = self.transform(image)

        return image, label

# Transformation for synthetic MNIST images
transform_mnist = transforms.Compose([
    transforms.Resize((28, 28)),
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,))
])

# Load the synthetic MNIST dataset
synthetic_mnist_dir = '/content/synthetic_images'  # Replace with the path to your synthetic MNIST images
synthetic_mnist_dataset = SyntheticMNISTDataset(synthetic_mnist_dir, transform=transform_mnist)
synthetic_mnist_loader = DataLoader(synthetic_mnist_dataset, batch_size=16, shuffle=True)

# Load the original MNIST test dataset
transform_test = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,))
])
original_mnist_test = datasets.MNIST(root='./data', train=False, transform=transform_test, download=True)
original_mnist_test_loader = DataLoader(original_mnist_test, batch_size=256, shuffle=False)

# Define the NAS search space
search_space = [
    {"num_conv_layers": 2, "num_filters": 16},
    {"num_conv_layers": 2, "num_filters": 32},
    {"num_conv_layers": 3, "num_filters": 16},
    {"num_conv_layers": 3, "num_filters": 32},
]

# Training and evaluation function for NAS
def train_and_evaluate(model, dataloader, epochs=10, lr=0.001):
    model = model.to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    # Training
    model.train()
    for epoch in range(epochs):
        running_loss = 0.0
        correct = 0
        total = 0
        for images, labels in dataloader:
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

        epoch_loss = running_loss / len(dataloader.dataset)
        epoch_accuracy = 100.0 * correct / total
        print(f"Epoch [{epoch+1}/{epochs}], Loss: {epoch_loss:.4f}, Accuracy: {epoch_accuracy:.2f}%")

    # Evaluation (return accuracy as a metric for NAS)
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for images, labels in dataloader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    accuracy = 100 * correct / total
    return accuracy

# Perform NAS
best_accuracy = 0
best_architecture = None
best_model = None

for config in search_space:
    print(f"Evaluate architecture: Conv = {config['num_conv_layers']} & {config['num_filters']} filters")
    model = SimpleCNN(num_channels=1, num_classes=10, **config)  # 1 channel for grayscale images
    accuracy = train_and_evaluate(model, synthetic_mnist_loader, epochs=10)
    print(f"Conv = {config['num_conv_layers']} & {config['num_filters']} filters with accuracy = {accuracy:.2f}%\n")

    # Keep track of the best-performing architecture
    if accuracy > best_accuracy:
        best_accuracy = accuracy
        best_architecture = config
        best_model = model

print(f"\nBest Architecture: Conv = {best_architecture['num_conv_layers']} & {best_architecture['num_filters']} filters, Accuracy on Synthetic Dataset: {best_accuracy:.2f}%")

# Retrain and evaluate the best model on the original MNIST test dataset
def retrain_and_evaluate_on_original(model, synthetic_loader, original_test_loader, epochs=10, lr=0.001):
    model = model.to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    # Retraining on synthetic dataset
    model.train()
    for epoch in range(epochs):
        running_loss = 0.0
        correct = 0
        total = 0
        for images, labels in synthetic_loader:
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

        epoch_loss = running_loss / len(synthetic_loader.dataset)
        epoch_accuracy = 100.0 * correct / total
        print(f"Epoch [{epoch+1}/{epochs}], Loss: {epoch_loss:.4f}, Accuracy: {epoch_accuracy:.2f}%")

    # Evaluation on original MNIST test set
    model.eval()
    correct = 0
    total = 0
    test_loss = 0.0
    with torch.no_grad():
        for images, labels in original_test_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)
            test_loss += loss.item() * images.size(0)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    test_accuracy = 100 * correct / total
    average_test_loss = test_loss / total
    print(f"\nTest Loss on original MNIST test set: {average_test_loss:.4f}")
    print(f"Test Accuracy on original MNIST test set: {test_accuracy:.2f}%")
    return test_accuracy

print("\nRetrain on best architecture on synthetic MNIST dataset")
final_accuracy = retrain_and_evaluate_on_original(best_model, synthetic_mnist_loader, original_mnist_test_loader, epochs=10)
print(f"Final Test Accuracy on original MNIST test set: {final_accuracy:.2f}%")

"""////QUESTION 4

"""

import os
import time
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import datasets, transforms
from PIL import Image

# Set device to GPU if available
device = 'cuda' if torch.cuda.is_available() else 'cpu'

# Define a modified BasicCNN model for NAS with additional features
class BasicCNN(nn.Module):
    def __init__(self, num_classes, num_conv_layers, num_filters, num_fc_units=128, activation_function='relu'):
        super(BasicCNN, self).__init__()
        layers = []
        in_channels = 3

        # Set activation function
        if activation_function == 'relu':
            activation = nn.ReLU(inplace=True)
        elif activation_function == 'leaky_relu':
            activation = nn.LeakyReLU(0.1, inplace=True)
        else:
            raise ValueError(f"Unsupported activation function: {activation_function}")

        # Add convolutional layers dynamically based on NAS config
        for _ in range(num_conv_layers):
            layers.append(nn.Conv2d(in_channels, num_filters, kernel_size=3, padding=1))
            layers.append(activation)
            layers.append(nn.MaxPool2d(kernel_size=2, stride=2))
            in_channels = num_filters

        self.features = nn.Sequential(*layers)

        # Add fully connected layers with configurable number of units
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(num_filters * (128 // (2 ** num_conv_layers)) ** 2, num_fc_units),
            activation,
            nn.Linear(num_fc_units, num_classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

# Define synthetic dataset loader
class SyntheticDataset(Dataset):
    def __init__(self, img_dir, transform=None):
        self.img_dir = img_dir
        self.transform = transform
        self.images = []
        self.labels = []

        for img_name in os.listdir(img_dir):
            label = int(img_name.split('_')[1])
            img_path = os.path.join(img_dir, img_name)
            self.images.append(img_path)
            self.labels.append(label)

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img_path = self.images[idx]
        image = Image.open(img_path).convert('RGB')  # Convert to RGB
        label = self.labels[idx]

        if self.transform:
            image = self.transform(image)

        return image, label

# Define real MHIST dataset loader with label mapping
class RealMHISTDataset(Dataset):
    def __init__(self, img_dir, csv_file, transform=None):
        self.img_dir = img_dir
        self.annotations = pd.read_csv(csv_file)
        self.transform = transform

        label_mapping = {'SSA': 0, 'HP': 1}
        self.images = []
        self.labels = []

        for _, row in self.annotations.iterrows():
            img_name = row['Image Name']
            label_str = row['Majority Vote Label']
            if label_str in label_mapping:
                int_label = label_mapping[label_str]
                self.images.append(img_name)
                self.labels.append(int_label)

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img_path = os.path.join(self.img_dir, self.images[idx])
        image = Image.open(img_path).convert('RGB')  # Convert to RGB
        label = self.labels[idx]

        if self.transform:
            image = self.transform(image)

        return image, label

# Data transformations with consistent 3-channel RGB format
transform_common = transforms.Compose([
    transforms.Grayscale(num_output_channels=3),  # Convert to 3-channel RGB for grayscale images like MNIST
    transforms.Resize((128, 128)),
    transforms.ToTensor(),
    transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))
])

# Load synthetic datasets with batch size 10 for training
synthetic_mnist_dir = '/content/synthetic_images_real_mnist'
synthetic_mhist_dir = '/content/synthetic_images_real_mhist'
synthetic_mnist_dataset = SyntheticDataset(synthetic_mnist_dir, transform=transform_common)
synthetic_mhist_dataset = SyntheticDataset(synthetic_mhist_dir, transform=transform_common)

# Train loaders for synthetic datasets with minibatch size 10
synthetic_mnist_loader = DataLoader(synthetic_mnist_dataset, batch_size=10, shuffle=True)
synthetic_mhist_loader = DataLoader(synthetic_mhist_dataset, batch_size=10, shuffle=True)

# Load original MNIST and MHIST test datasets with minibatch size 256
mnist_test_dataset = datasets.MNIST(root='./data', train=False, transform=transform_common, download=True)
mnist_test_loader = DataLoader(mnist_test_dataset, batch_size=256, shuffle=False)

mhist_images_dir = '/content/Mydrive/MyDrive/submission_files1/mhist_dataset/images'
mhist_annotations_file = '/content/Mydrive/MyDrive/submission_files1/mhist_dataset/annotations.csv'
real_mhist_test_dataset = RealMHISTDataset(mhist_images_dir, mhist_annotations_file, transform=transform_common)
mhist_test_loader = DataLoader(real_mhist_test_dataset, batch_size=256, shuffle=False)

# Define search space
search_space = [
    {"num_conv_layers": 2, "num_filters": 16, "num_fc_units": 64, "activation_function": 'relu'},
    {"num_conv_layers": 2, "num_filters": 32, "num_fc_units": 128, "activation_function": 'relu'},
    {"num_conv_layers": 3, "num_filters": 16, "num_fc_units": 128, "activation_function": 'leaky_relu'},
    {"num_conv_layers": 3, "num_filters": 32, "num_fc_units": 256, "activation_function": 'leaky_relu'},
    {"num_conv_layers": 4, "num_filters": 32, "num_fc_units": 128, "activation_function": 'relu'},
    {"num_conv_layers": 4, "num_filters": 64, "num_fc_units": 256, "activation_function": 'relu'}
]

# Training and evaluation function
def train_and_evaluate(model, dataloader, epochs=10, lr=0.001):
    model = model.to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    model.train()
    for epoch in range(epochs):
        running_loss = 0.0
        correct = 0
        total = 0
        for images, labels in dataloader:
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

        epoch_loss = running_loss / len(dataloader.dataset)
        epoch_accuracy = 100.0 * correct / total
        print(f"Epoch [{epoch+1}/{epochs}], Loss: {epoch_loss:.4f}, Accuracy: {epoch_accuracy:.2f}%")

    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for images, labels in dataloader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    accuracy = 100 * correct / total
    return accuracy

# Define a function to retrain the best model on the synthetic dataset and evaluate it on the original test dataset
def retrain_and_evaluate_on_original(model, synthetic_loader, original_test_loader, epochs=10, lr=0.001):
    model = model.to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    # Retraining on synthetic dataset
    model.train()
    for epoch in range(epochs):
        running_loss = 0.0
        correct = 0
        total = 0
        for images, labels in synthetic_loader:
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

        epoch_loss = running_loss / len(synthetic_loader.dataset)
        epoch_accuracy = 100.0 * correct / total
        print(f"Epoch [{epoch+1}/{epochs}], Loss: {epoch_loss:.4f}, Accuracy: {epoch_accuracy:.2f}%")

    # Evaluation on original test set
    model.eval()
    correct = 0
    total = 0
    test_loss = 0.0
    with torch.no_grad():
        for images, labels in original_test_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)
            test_loss += loss.item() * images.size(0)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    test_accuracy = 100 * correct / total
    average_test_loss = test_loss / total
    print(f"\nTest Loss on original test set: {average_test_loss:.4f}")
    print(f"Test Accuracy on original test set: {test_accuracy:.2f}%")
    return test_accuracy

# Running NAS and training for both MNIST and MHIST
datasets_to_train = [
    ("MNIST", synthetic_mnist_loader, mnist_test_loader, 10),
    ("MHIST", synthetic_mhist_loader, mhist_test_loader, 2)
]

for dataset_name, train_loader, test_loader, num_classes in datasets_to_train:
    print(f"\nRunning NAS and training for {dataset_name} dataset.")
    best_accuracy = 0
    best_architecture = None
    best_model = None

    for config in search_space:
        print(f"Evaluate architecture: Conv = {config['num_conv_layers']} & {config['num_filters']} filters, "
              f"FC Units = {config['num_fc_units']}, Activation = {config['activation_function']} on {dataset_name}")

        # Initialize the model with the additional parameters
        model = BasicCNN(
            num_classes=num_classes,
            num_conv_layers=config["num_conv_layers"],
            num_filters=config["num_filters"],
            num_fc_units=config["num_fc_units"],
            activation_function=config["activation_function"]
        )

        accuracy = train_and_evaluate(model, train_loader, epochs=10)
        print(f"{dataset_name} -> Conv = {config['num_conv_layers']} & {config['num_filters']} filters, "
              f"FC Units = {config['num_fc_units']}, Activation = {config['activation_function']} with accuracy = {accuracy:.2f}%\n")

        # Track best-performing model
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_architecture = config
            best_model = model

    print(f"\nBest Architecture for {dataset_name}: Conv = {best_architecture['num_conv_layers']} & {best_architecture['num_filters']} filters, "
          f"FC Units = {best_architecture['num_fc_units']}, Activation = {best_architecture['activation_function']}, "
          f"Accuracy on Synthetic Dataset: {best_accuracy:.2f}%")

    # Retrain and evaluate the best model on the synthetic dataset and original test dataset
    print(f"\nRetraining best architecture on synthetic {dataset_name} dataset and evaluating on original {dataset_name} test set:")
    final_test_accuracy = retrain_and_evaluate_on_original(best_model, train_loader, test_loader, epochs=10)
    print(f"Final Test Accuracy on original {dataset_name} test set: {final_test_accuracy:.2f}%")