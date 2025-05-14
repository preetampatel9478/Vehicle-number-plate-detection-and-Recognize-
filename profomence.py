import matplotlib.pyplot as plt
import numpy as np

def create_system_performance():
    plt.figure(figsize=(12, 6))
    metrics = ['Vehicle\nDetection', 'Speed\nCalculation', 'Plate\nRecognition', 'Database\nOperations']
    
    accuracy = [96, 94, 92, 98]
    response_time = [35, 42, 85, 25]
    reliability = [95, 92, 88, 97]
    efficiency = [94, 90, 87, 96]
    
    x = np.arange(len(metrics))
    width = 0.2
    
    plt.bar(x - width*1.5, accuracy, width, label='Accuracy (%)', color='#0078D7')
    plt.bar(x - width/2, response_time, width, label='Response Time (ms)', color='#00B294')
    plt.bar(x + width/2, reliability, width, label='Reliability (%)', color='#881798')
    plt.bar(x + width*1.5, efficiency, width, label='Efficiency (%)', color='#FF8C00')
    
    plt.xlabel('System Components')
    plt.ylabel('Performance Metrics')
    plt.title('System Performance Analysis')
    plt.xticks(x, metrics)
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Save the plot
    plt.savefig('performance_metrics.png')
    # Show the plot
    plt.show()

# Main execution
if __name__ == "__main__":
    create_system_performance()