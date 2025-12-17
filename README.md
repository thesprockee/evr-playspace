# evr-playspace

Detect playspacing in EchoVR by using machine learning to analyze player movement patterns.

## Overview

This project implements an ETL pipeline and anomaly detection system for EchoVR game data:

1. **Go ETL Tool**: Reads EchoVR JSON from stdin, tracks player state (position, velocity, acceleration), calculates Jerk (rate of change of acceleration), and outputs to Parquet format.

2. **Python Analysis Script**: Loads the Parquet data, groups by 1-second windows, trains an IsolationForest model to detect anomalies, and visualizes suspect Jerk profiles.

## Components

### 1. Go ETL Tool (`main.go`)

The ETL tool processes streaming EchoVR JSON data:

- **Input**: JSON lines from stdin, each containing:
  - `sessionid`: Game session identifier
  - `game_clock`: Game time in seconds
  - `teams`: Array of teams, each with players
  - Each player has `userid`, `position` (x,y,z), and `velocity` (x,y,z)

- **Processing**:
  - Tracks player state per `sessionid+userid` combination
  - Calculates acceleration from velocity changes
  - Calculates Jerk as the magnitude of acceleration change
  
- **Output**: `features.parquet` with columns:
  - `SessionID`: Session identifier
  - `UserID`: User identifier  
  - `Time`: Game clock time
  - `Jerk`: Calculated jerk value

### 2. Python Analysis Script (`analyze.py`)

Analyzes the Parquet data to detect anomalous player movement:

- Groups data by 1-second windows and calculates max Jerk per window
- Trains IsolationForest model with contamination=0.005 (0.5% expected anomalies)
- Generates visualizations showing:
  - Distribution of Jerk values (normal vs anomalous)
  - Time series of Jerk with anomalies highlighted

## Installation

### Go Dependencies

```bash
go mod download
```

### Python Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### 1. Build the Go ETL Tool

```bash
go build -o etl main.go
```

### 2. Process EchoVR Data

Feed JSON data through stdin:

```bash
cat sample_data.jsonl | ./etl
```

This will create `features.parquet` with the calculated Jerk values.

### 3. Run Anomaly Detection

```bash
python3 analyze.py
```

This will:
- Load `features.parquet`
- Group by 1-second windows
- Train the IsolationForest model
- Print summary statistics
- Generate `jerk_anomalies.png` with visualization

## Sample Data Format

The ETL tool expects JSON lines with the following structure:

```json
{
  "sessionid": "session001",
  "game_clock": 1.5,
  "teams": [
    {
      "players": [
        {
          "userid": "user1",
          "position": {"x": 1.0, "y": 2.0, "z": 3.0},
          "velocity": {"x": 0.5, "y": 0.0, "z": 0.1}
        }
      ]
    }
  ]
}
```

A sample dataset is provided in `sample_data.jsonl` for testing.

## Example Workflow

```bash
# Build the ETL tool
go build -o etl main.go

# Process sample data
cat sample_data.jsonl | ./etl

# Install Python dependencies
pip install -r requirements.txt

# Run analysis
python3 analyze.py
```

## Output

- `features.parquet`: Processed movement data with Jerk calculations
- `jerk_anomalies.png`: Visualization showing Jerk distribution and time series with anomalies highlighted

## Technical Details

### Jerk Calculation

Jerk is the rate of change of acceleration, calculated as:

1. Acceleration = change in velocity between frames
2. Jerk = magnitude of change in acceleration between frames

Higher jerk values indicate rapid changes in movement patterns, which may indicate unnatural or "playspacing" behavior.

### Anomaly Detection

The IsolationForest algorithm is used because:
- It's effective for high-dimensional data
- It doesn't require labeled data
- It's efficient for detecting outliers in continuous data
- The contamination parameter (0.005) assumes 0.5% of behavior is anomalous

## License

MIT

