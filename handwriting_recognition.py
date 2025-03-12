import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt

# Step 1: Load and preprocess the MNIST dataset
def load_data():
    # Load MNIST dataset
    (x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()
    
    # Normalize the pixel values to be between 0 and 1
    x_train = x_train.astype('float32') / 255.0
    x_test = x_test.astype('float32') / 255.0
    
    # Reshape the data to match the CNN input shape (28x28x1)
    x_train = x_train.reshape(-1, 28, 28, 1)
    x_test = x_test.reshape(-1, 28, 28, 1)
    
    return (x_train, y_train), (x_test, y_test)

# Step 2: Create the CNN model
def create_model():
    model = tf.keras.Sequential([
        # First Convolutional Layer
        tf.keras.layers.Conv2D(32, (3, 3), activation='relu', input_shape=(28, 28, 1)),
        tf.keras.layers.MaxPooling2D((2, 2)),
        
        # Second Convolutional Layer
        tf.keras.layers.Conv2D(64, (3, 3), activation='relu'),
        tf.keras.layers.MaxPooling2D((2, 2)),
        
        # Third Convolutional Layer
        tf.keras.layers.Conv2D(64, (3, 3), activation='relu'),
        
        # Flatten the output
        tf.keras.layers.Flatten(),
        
        # Dense layers
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(10, activation='softmax')
    ])
    
    return model

# Step 3: Train the model
def train_model(model, x_train, y_train):
    # Compile the model
    model.compile(optimizer='adam',
                 loss='sparse_categorical_crossentropy',
                 metrics=['accuracy'])
    
    # Train the model
    history = model.fit(x_train, y_train,
                       epochs=5,
                       batch_size=64,
                       validation_split=0.2)
    
    return history

# Step 4: Evaluate the model
def evaluate_model(model, x_test, y_test):
    test_loss, test_accuracy = model.evaluate(x_test, y_test)
    print(f"\nTest accuracy: {test_accuracy:.4f}")
    return test_loss, test_accuracy

# Step 5: Make predictions and visualize results
def visualize_predictions(model, x_test, y_test, num_images=5):
    # Get random sample of images
    indices = np.random.randint(0, len(x_test), num_images)
    sample_images = x_test[indices]
    sample_labels = y_test[indices]
    
    # Make predictions
    predictions = model.predict(sample_images)
    predicted_labels = np.argmax(predictions, axis=1)
    
    # Plot the results
    plt.figure(figsize=(15, 3))
    for i in range(num_images):
        plt.subplot(1, num_images, i + 1)
        plt.imshow(sample_images[i].reshape(28, 28), cmap='gray')
        plt.title(f'Pred: {predicted_labels[i]}\nTrue: {sample_labels[i]}')
        plt.axis('off')
    plt.show()

def main():
    # Load data
    print("Loading data...")
    (x_train, y_train), (x_test, y_test) = load_data()
    
    # Create model
    print("Creating model...")
    model = create_model()
    model.summary()
    
    # Train model
    print("Training model...")
    history = train_model(model, x_train, y_train)
    
    # Evaluate model
    print("Evaluating model...")
    evaluate_model(model, x_test, y_test)
    
    # Visualize predictions
    print("Visualizing predictions...")
    visualize_predictions(model, x_test, y_test)

if __name__ == "__main__":
    main() 