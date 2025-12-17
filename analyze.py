#!/usr/bin/env python3
"""
Analyze Jerk data from features.parquet to detect anomalies using IsolationForest.
Groups by 1-second windows, calculates max Jerk, trains model, and plots results.
"""

import polars as pl
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
import numpy as np

def load_and_prepare_data(parquet_file='features.parquet'):
    """Load parquet file and prepare data."""
    print(f"Loading data from {parquet_file}...")
    df = pl.read_parquet(parquet_file)
    print(f"Loaded {len(df)} records")
    print(f"Columns: {df.columns}")
    return df

def group_by_windows(df):
    """Group by 1-second windows and calculate max Jerk."""
    print("\nGrouping by 1-second windows...")
    
    # Create time window by flooring the time to nearest second
    df = df.with_columns([
        pl.col("time").floor().alias("time_window")
    ])
    
    # Group by session, user, and time window, calculate max jerk
    grouped = df.group_by(["sessionid", "userid", "time_window"]).agg([
        pl.col("jerk").max().alias("max_jerk")
    ]).sort(["sessionid", "userid", "time_window"])
    
    print(f"Created {len(grouped)} 1-second window aggregates")
    return grouped

def train_isolation_forest(df):
    """Train IsolationForest model to detect anomalies."""
    print("\nTraining IsolationForest model...")
    
    # Prepare features for model
    X = df.select("max_jerk").to_numpy()
    
    # Train IsolationForest with contamination=0.005 (0.5% anomalies expected)
    model = IsolationForest(contamination=0.005, random_state=42, n_jobs=-1)
    predictions = model.fit_predict(X)
    
    # Add predictions to dataframe (-1 for anomalies, 1 for normal)
    df = df.with_columns([
        pl.Series("is_anomaly", predictions == -1)
    ])
    
    n_anomalies = (predictions == -1).sum()
    print(f"Detected {n_anomalies} anomalies ({n_anomalies/len(df)*100:.2f}%)")
    
    return df, model

def plot_anomalies(df, max_users=5):
    """Plot Jerk profiles with highlighted anomalies.
    
    Args:
        df: DataFrame with jerk data and anomaly predictions
        max_users: Maximum number of users to display in time series plot (default: 5)
    """
    print("\nGenerating plots...")
    
    # Get anomalies
    anomalies = df.filter(pl.col("is_anomaly"))
    normal = df.filter(~pl.col("is_anomaly"))
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    # Plot 1: Distribution of max Jerk values
    ax1 = axes[0]
    normal_jerk = normal.select("max_jerk").to_numpy().flatten()
    anomaly_jerk = anomalies.select("max_jerk").to_numpy().flatten()
    
    ax1.hist(normal_jerk, bins=50, alpha=0.7, label='Normal', color='blue')
    ax1.hist(anomaly_jerk, bins=20, alpha=0.7, label='Anomalies', color='red')
    ax1.set_xlabel('Max Jerk')
    ax1.set_ylabel('Frequency')
    ax1.set_title('Distribution of Max Jerk Values (1s windows)')
    ax1.legend()
    ax1.set_yscale('log')
    
    # Plot 2: Time series of Jerk with anomalies highlighted
    ax2 = axes[1]
    
    # For time series, we'll plot each user separately (limiting for clarity)
    unique_users = df.select("userid").unique().to_series().to_list()[:max_users]
    
    colors = plt.cm.tab10(range(len(unique_users)))
    
    for i, user in enumerate(unique_users):
        user_data = df.filter(pl.col("userid") == user).sort("time_window")
        user_anomalies = user_data.filter(pl.col("is_anomaly"))
        
        times = user_data.select("time_window").to_numpy().flatten()
        jerks = user_data.select("max_jerk").to_numpy().flatten()
        
        # Plot normal points
        ax2.plot(times, jerks, alpha=0.6, label=f'User {user[:8]}', color=colors[i])
        
        # Highlight anomalies
        if len(user_anomalies) > 0:
            anom_times = user_anomalies.select("time_window").to_numpy().flatten()
            anom_jerks = user_anomalies.select("max_jerk").to_numpy().flatten()
            ax2.scatter(anom_times, anom_jerks, color='red', s=100, marker='x', 
                       linewidths=3, zorder=5)
    
    ax2.set_xlabel('Time (seconds)')
    ax2.set_ylabel('Max Jerk')
    ax2.set_title('Jerk Over Time (Anomalies marked with red X)')
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot
    output_file = 'jerk_anomalies.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"Plot saved to {output_file}")
    
    # Also display if running interactively
    plt.show()
    
    return fig

def print_summary(df):
    """Print summary statistics."""
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)
    
    anomalies = df.filter(pl.col("is_anomaly"))
    
    print(f"\nTotal windows: {len(df)}")
    print(f"Anomalous windows: {len(anomalies)}")
    print(f"Percentage anomalous: {len(anomalies)/len(df)*100:.2f}%")
    
    print(f"\nMax Jerk statistics:")
    print(f"  Mean: {df.select('max_jerk').mean().item():.4f}")
    print(f"  Median: {df.select('max_jerk').median().item():.4f}")
    print(f"  Std: {df.select('max_jerk').std().item():.4f}")
    print(f"  Min: {df.select('max_jerk').min().item():.4f}")
    print(f"  Max: {df.select('max_jerk').max().item():.4f}")
    
    if len(anomalies) > 0:
        print(f"\nAnomalous Jerk statistics:")
        print(f"  Mean: {anomalies.select('max_jerk').mean().item():.4f}")
        print(f"  Median: {anomalies.select('max_jerk').median().item():.4f}")
        print(f"  Min: {anomalies.select('max_jerk').min().item():.4f}")
        print(f"  Max: {anomalies.select('max_jerk').max().item():.4f}")
        
        print("\nTop 10 anomalous windows:")
        top_anomalies = anomalies.sort("max_jerk", descending=True).head(10)
        print(top_anomalies)

def main():
    """Main analysis pipeline."""
    print("Starting Jerk Anomaly Detection Analysis")
    print("="*60)
    
    # Load data
    df = load_and_prepare_data()
    
    # Group by windows
    grouped = group_by_windows(df)
    
    # Train model and detect anomalies
    result_df, model = train_isolation_forest(grouped)
    
    # Print summary
    print_summary(result_df)
    
    # Plot results
    plot_anomalies(result_df)
    
    print("\n" + "="*60)
    print("Analysis complete!")
    print("="*60)

if __name__ == "__main__":
    main()
