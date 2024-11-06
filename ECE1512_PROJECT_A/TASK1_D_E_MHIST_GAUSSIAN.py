# -*- coding: utf-8 -*-
"""TASK1_D_E_mhist_gaussain.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1ZcRg0fXjd8lRj84aCcMmI3ggE41eHvQQ
"""

import matplotlib.pyplot as plt
import torch
import torch.optim as optim
from torch import nn
from torch.utils.data import DataLoader,Dataset
from torchvision import transforms
import random
import pandas as pd
from PIL import Image
from networks import ConvNet

from google.colab import drive
import os
drive.mount('/content/Mydrive')
# Set the path to MHIST dataset
data_path = '/content/MyDrive/MyDrive/submission_files1/mhist_dataset'
annotations_file = '/content/MyDrive/MyDrive/submission_files1/mhist_dataset/annotations.csv'
img_dir = '/content/Mydrive/MyDrive/submission_files1/mhist_dataset/images'
# Set device to GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Define MHIST Dataset Class
class MHISTDataset(Dataset):
    def __init__(self, annotations_file, img_dir, transform=None):
        self.img_labels = pd.read_csv("/content/Mydrive/MyDrive/submission_files1/mhist_dataset/annotations.csv")
        self.img_dir = img_dir
        self.transform = transform
        self.label_map = {"HP": 0, "SSA": 1}

    def __len__(self):
        return len(self.img_labels)

    def __getitem__(self, idx):
        img_path = os.path.join(self.img_dir, self.img_labels.iloc[idx, 0])
        image = Image.open(img_path).convert("RGB")
        label = self.img_labels.iloc[idx, 1]
        label = self.label_map[label]
        if self.transform:
            image = self.transform(image)
        return image, label

# Define transformations for MHIST images
transform = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Load MHIST dataset
train_data = MHISTDataset(annotations_file=annotations_file, img_dir=img_dir, transform=transform)
train_loader = DataLoader(train_data, batch_size=128, shuffle=True)

def run_attention_matching_mhist_gaussian(
    num_weight_initializations=20,
    model_update_steps=50,
    lr_synthetic=0.1,
    synthetic_update_steps=1,
    lr_model=0.01,
    task_balance_lambda=0.01,
    num_epochs=10,
    images_per_class=50,
    minibatch_size=128
):
    # Initialize synthetic data with Gaussian noise
    num_classes = 2
    synthetic_data = []

    # Generate Gaussian noise for each class
    for _ in range(num_classes):
        class_tensor = torch.randn((images_per_class, 3, 128, 128), device=device, requires_grad=True)
        synthetic_data.append(class_tensor)

    # Generate labels for the synthetic dataset
    synthetic_labels = torch.tensor([i for i in range(num_classes) for _ in range(images_per_class)], device=device)

    # Attention Matching Process (rest of the function remains unchanged)
    for epoch in range(num_epochs):
        print(f"Epoch {epoch+1}/{num_epochs}")
        epoch_loss = 0  # Track loss for each epoch

        for weight_init_iter in range(num_weight_initializations):
            # Initialize the ConvNet model for each reinitialization
            model = ConvNet(
                channel=3, num_classes=2, net_width=128, net_depth=7,
                net_act='relu', net_norm='instancenorm', net_pooling='avgpooling', im_size=(128, 128)
            ).to(device)

            model_optimizer = optim.SGD(model.parameters(), lr=lr_model, momentum=0.9)

            # Model training on synthetic data for `model_update_steps` iterations
            for update_step in range(model_update_steps):
                synthetic_inputs = torch.cat([sd.clone().detach().requires_grad_(True) for sd in synthetic_data]).to(device)

                model_output = model(synthetic_inputs)
                model_loss = nn.CrossEntropyLoss()(model_output, synthetic_labels)

                model_optimizer.zero_grad()
                model_loss.backward()
                model_optimizer.step()
                epoch_loss += model_loss.item()

            # Update synthetic data with attention matching
            for synthetic_step in range(synthetic_update_steps):
                for class_idx, synthetic_class_data in enumerate(synthetic_data):
                    synthetic_class_data = synthetic_class_data.clone().detach().requires_grad_(True)
                    synthetic_optimizer = optim.SGD([synthetic_class_data], lr=lr_synthetic)

                    real_images, real_labels = next(iter(train_loader))
                    real_images, real_labels = real_images.to(device), real_labels.to(device)

                    model.eval()
                    synthetic_output = model(synthetic_class_data)
                    real_output = model(real_images)

                    attention_loss = task_balance_lambda * ((synthetic_output - real_output[:images_per_class].detach()) ** 2).mean()

                    synthetic_optimizer.zero_grad()
                    attention_loss.backward()
                    synthetic_optimizer.step()

                    synthetic_data[class_idx] = synthetic_class_data.detach().requires_grad_(True)

        print(f"Epoch {epoch+1} Completed - Average Loss: {epoch_loss / (num_weight_initializations * model_update_steps):.4f}")

    # Visualize the condensed synthetic images
    save_synthetic_images(synthetic_data)

    # Evaluate the model on the test set
    test_data = MHISTDataset(annotations_file=annotations_file, img_dir=img_dir, transform=transform)
    test_loader = DataLoader(test_data, batch_size=256, shuffle=False)
    evaluate_model(model, test_loader)

import os
from torchvision.utils import save_image

def save_synthetic_images(synthetic_data, save_dir="synthetic_images"):
    os.makedirs(save_dir, exist_ok=True)  # Create directory to save images

    num_classes = len(synthetic_data)
    images_per_class = synthetic_data[0].shape[0]  # Number of images per class

    for class_idx, class_data in enumerate(synthetic_data):
        for img_idx in range(images_per_class):
            # Extract each image, resize to 28x28 if necessary, and save it
            image = class_data[img_idx].detach().cpu()

            # Save each image with a specific filename
            filename = f"{save_dir}/class_{class_idx}_image_{img_idx + 1}.png"
            save_image(image, filename)
            #print(f"Saved {filename}")

# Evaluation function to test the accuracy of attention matching on real MHIST test data
def evaluate_model(model, test_loader):
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

    test_accuracy = correct / total
    print(f"Test Accuracy: {test_accuracy:.2f}")

run_attention_matching_mhist_gaussian()

!pip install ptflops
!pip install torchprofile

import time
from torch.optim.lr_scheduler import CosineAnnealingLR
from ptflops import get_model_complexity_info

# SyntheticMHISTDataset class to load synthetic images
class SyntheticMHISTDataset(Dataset):
    def __init__(self, img_dir, transform=None):
        self.img_dir = img_dir
        self.transform = transform
        self.images = []
        self.labels = []

        # Load all synthetic image paths and labels from directory
        for class_idx in range(2):  # Assuming 2 classes for MHIST
            for img_idx in range(1, 51):  # 50 images per class
                img_name = f"class_{class_idx}_image_{img_idx}.png"
                img_path = os.path.join(img_dir, img_name)
                if os.path.exists(img_path):
                    self.images.append(img_path)
                    self.labels.append(class_idx)

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img_path = self.images[idx]
        image = Image.open(img_path).convert("RGB")
        label = self.labels[idx]
        if self.transform:
            image = self.transform(image)
        return image, label

# Define transform for synthetic MHIST images
transform = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Updated get_dataset function to use synthetic images for training and original for testing
def get_dataset(dataset_name):
    if dataset_name == 'MHIST':
        # Load synthetic data for training
        synthetic_train_data = SyntheticMHISTDataset(img_dir='/content/synthetic_images', transform=transform)
        train_loader = DataLoader(synthetic_train_data, batch_size=10, shuffle=True)

        test_data = MHISTDataset(annotations_file=annotations_file, img_dir=img_dir, transform=transform)
        test_loader = DataLoader(test_data, batch_size=128, shuffle=False)

        # Initialize the ConvNet model for MHIST
        model = ConvNet(
            channel=3,
            num_classes=2,
            net_width=128,
            net_depth=7,
            net_act='relu',
            net_norm='instancenorm',
            net_pooling='avgpooling',
            im_size=(128, 128)
        ).to(device)

        dummy_input = torch.randn(1, 3, 128, 128)


    return train_loader, test_loader, model, dummy_input

# Function to calculate FLOPs and parameter count
def calculate_flops(model, input_res=(3, 128, 128)):
    flops, params = get_model_complexity_info(model, input_res, as_strings=True, print_per_layer_stat=False)
    #print(f"FLOPs: {flops}")
    return flops, params

# Training function with runtime recording
def train_synthetic_model(model, train_loader, optimizer, scheduler, criterion, num_epochs=20):
    model.train()
    start_time = time.time()  # Start recording training time
    for epoch in range(num_epochs):
        running_loss = 0.0
        correct = 0
        total = 0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            # Accumulate loss
            running_loss += loss.item() * images.size(0)

            # Calculate accuracy
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

        # Calculate average loss and accuracy for the epoch
        epoch_loss = running_loss / len(train_loader.dataset)
        epoch_accuracy = 100 * correct / total

        scheduler.step()
        print(f"Epoch [{epoch+1}/{num_epochs}], Loss: {epoch_loss:.4f}, Accuracy: {epoch_accuracy:.2f}%")
    end_time = time.time()  # End recording training time
    training_runtime = end_time - start_time
    print(f"Total Training Time: {training_runtime:.2f} seconds")

# Testing function with runtime recording
def test_model_with_runtime(model, test_loader):
    model.eval()
    correct = 0
    total = 0
    start_time = time.time()  # Start recording time
    with torch.no_grad():
        for images, labels in test_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    end_time = time.time()  # End recording time
    test_runtime = end_time - start_time
    accuracy = 100 * correct / total
    print(f"Test Accuracy: {accuracy:.2f}%")
    print(f"Test Runtime: {test_runtime:.2f} seconds")
    return accuracy, test_runtime

# Get the dataset, model, and dataloaders
train_loader, test_loader, model, dummy_input = get_dataset('MHIST')

# Set up optimizer, scheduler, and loss function
optimizer = optim.SGD(model.parameters(), lr=0.01, momentum=0.9)
scheduler = CosineAnnealingLR(optimizer, T_max=20)
criterion = nn.CrossEntropyLoss().to(device)

# Calculate FLOPs and Params
calculate_flops(model, input_res=(3, 128, 128))

# Train the model using synthetic dataset
train_synthetic_model(model, train_loader, optimizer, scheduler, criterion, num_epochs=20)

# Test the model on the original test dataset
accuracy, runtime = test_model_with_runtime(model, test_loader)