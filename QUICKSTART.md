# Quick Start Guide

This guide will help you get started with the EchoVR playspacing detection pipeline.

## Prerequisites

- Go 1.21 or later
- Python 3.8 or later
- pip (Python package manager)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/thesprockee/evr-playspace.git
cd evr-playspace
```

### 2. Build the Go ETL Tool

```bash
go build -o etl main.go
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

## Running the Pipeline

### Step 1: Process EchoVR Data

Feed your EchoVR JSON data through stdin:

```bash
cat your_data.jsonl | ./etl
```

Or use the provided test data:

```bash
cat test_data.jsonl | ./etl
```

This will create `features.parquet` with calculated Jerk values.

### Step 2: Analyze and Detect Anomalies

```bash
python3 analyze.py
```

This will:
- Load the parquet data
- Group by 1-second windows
- Train the IsolationForest model
- Print statistics to console
- Generate `jerk_anomalies.png` visualization

## Understanding the Output

### Console Output

The script will print:
- Number of records processed
- Total windows analyzed
- Number and percentage of anomalies detected
- Statistical summary (mean, median, std, min, max)
- Top 10 anomalous windows

### Visualization (`jerk_anomalies.png`)

The output image contains two plots:

1. **Top plot**: Histogram showing distribution of Max Jerk values
   - Blue bars: Normal behavior
   - Red bars: Anomalous behavior
   - Note: Y-axis is logarithmic scale

2. **Bottom plot**: Time series of Jerk values over time
   - Different colored lines represent different users
   - Red X markers indicate detected anomalies
   - Helps identify when and for whom anomalies occurred

## Data Format

Your input JSON should be newline-delimited JSON (JSONL) with this structure:

```json
{
  "sessionid": "unique_session_id",
  "game_clock": 1.5,
  "teams": [
    {
      "players": [
        {
          "userid": "unique_user_id",
          "position": {"x": 1.0, "y": 2.0, "z": 3.0},
          "velocity": {"x": 0.5, "y": 0.0, "z": 0.1}
        }
      ]
    }
  ]
}
```

Each line should be a complete JSON object representing one frame of game data.

## Interpreting Results

### What is Jerk?

Jerk is the rate of change of acceleration. In the context of EchoVR:
- Low jerk values indicate smooth, natural movement
- High jerk values indicate rapid, jerky changes in movement
- Sudden spikes might indicate "playspacing" or other anomalous behavior

### Anomaly Threshold

The IsolationForest model uses `contamination=0.005`, meaning it expects about 0.5% of the data to be anomalous. This is a conservative threshold that should catch the most extreme outliers while minimizing false positives.

### Next Steps

1. **Investigate Anomalies**: Look at the specific sessionid, userid, and time stamps for detected anomalies
2. **Adjust Threshold**: If needed, modify the `contamination` parameter in `analyze.py`
3. **Review Video**: Cross-reference anomalous timestamps with game recordings
4. **Refine Model**: Add more features or use different algorithms based on your findings

## Troubleshooting

### "Not enough data" error

The IsolationForest requires a reasonable amount of data. Make sure you have:
- At least 100+ frames of data
- Multiple players/sessions
- Use the provided `test_data.jsonl` for testing

### Build errors

If you encounter Go build errors, ensure you have:
- Go 1.21+ installed
- Run `go mod tidy` to download dependencies
- Check that you're in the correct directory

### Python import errors

If you get import errors:
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Use a virtual environment if needed
- Check Python version: `python3 --version` (should be 3.8+)

## Advanced Usage

### Processing Live Data

You can pipe live data directly to the ETL tool:

```bash
your_echovr_capture_tool | ./etl
```

### Batch Processing

Process multiple files:

```bash
cat session1.jsonl session2.jsonl session3.jsonl | ./etl
python3 analyze.py
```

### Custom Analysis

Modify `analyze.py` to:
- Change window size (currently 1 second)
- Adjust contamination parameter
- Add more features for analysis
- Export results to different formats

## Support

For issues or questions, please open an issue on the GitHub repository.
