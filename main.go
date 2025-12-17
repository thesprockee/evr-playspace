package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"math"
	"os"

	"github.com/xitongsys/parquet-go-source/local"
	"github.com/xitongsys/parquet-go/writer"
)

// Vec3 represents a 3D vector
type Vec3 struct {
	X float64 `json:"x"`
	Y float64 `json:"y"`
	Z float64 `json:"z"`
}

// Magnitude returns the magnitude of a vector
func (v Vec3) Magnitude() float64 {
	return math.Sqrt(v.X*v.X + v.Y*v.Y + v.Z*v.Z)
}

// Sub returns the difference between two vectors
func (v Vec3) Sub(other Vec3) Vec3 {
	return Vec3{
		X: v.X - other.X,
		Y: v.Y - other.Y,
		Z: v.Z - other.Z,
	}
}

// Player represents a player in EchoVR
type Player struct {
	UserID   string `json:"userid"`
	Position Vec3   `json:"position"`
	Velocity Vec3   `json:"velocity"`
}

// EchoVRFrame represents a frame of data from EchoVR
type EchoVRFrame struct {
	SessionID string   `json:"sessionid"`
	Time      float64  `json:"game_clock"`
	Teams     []Team   `json:"teams"`
}

// Team represents a team with players
type Team struct {
	Players []Player `json:"players"`
}

// PlayerState tracks the state of a player across frames
type PlayerState struct {
	LastPosition Vec3
	LastVelocity Vec3
	LastAccel    Vec3
	HasPrevious  bool
}

// PlayerKey uniquely identifies a player in a session
type PlayerKey struct {
	SessionID string
	UserID    string
}

// JerkRecord represents a row in the output parquet file
type JerkRecord struct {
	SessionID string  `parquet:"name=sessionid, type=BYTE_ARRAY, convertedtype=UTF8"`
	UserID    string  `parquet:"name=userid, type=BYTE_ARRAY, convertedtype=UTF8"`
	Time      float64 `parquet:"name=time, type=DOUBLE"`
	Jerk      float64 `parquet:"name=jerk, type=DOUBLE"`
}

func main() {
	scanner := bufio.NewScanner(os.Stdin)
	states := make(map[PlayerKey]*PlayerState)
	var records []JerkRecord

	// Read JSON lines from stdin
	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}

		var frame EchoVRFrame
		if err := json.Unmarshal(line, &frame); err != nil {
			fmt.Fprintf(os.Stderr, "Error parsing JSON: %v\n", err)
			continue
		}

		// Process each player in each team
		for _, team := range frame.Teams {
			for _, player := range team.Players {
				key := PlayerKey{SessionID: frame.SessionID, UserID: player.UserID}
				state, exists := states[key]

				if !exists {
					// Initialize state for new player
					states[key] = &PlayerState{
						LastPosition: player.Position,
						LastVelocity: player.Velocity,
						HasPrevious:  false,
					}
					continue
				}

				// Calculate acceleration from velocity change
				// Note: This is a finite difference approximation without time normalization.
				// For proper physics calculations, this should be divided by deltaTime.
				// The current implementation assumes uniform time steps between frames.
				currentAccel := player.Velocity.Sub(state.LastVelocity)

				if state.HasPrevious {
					// Calculate jerk as the magnitude of change in acceleration
					accelChange := currentAccel.Sub(state.LastAccel)
					jerk := accelChange.Magnitude()

					// Record the jerk value
					records = append(records, JerkRecord{
						SessionID: frame.SessionID,
						UserID:    player.UserID,
						Time:      frame.Time,
						Jerk:      jerk,
					})
				}

				// Update state
				state.LastPosition = player.Position
				state.LastVelocity = player.Velocity
				state.LastAccel = currentAccel
				state.HasPrevious = true
			}
		}
	}

	if err := scanner.Err(); err != nil {
		fmt.Fprintf(os.Stderr, "Error reading stdin: %v\n", err)
		os.Exit(1)
	}

	// Write records to parquet file
	if len(records) > 0 {
		if err := writeParquet(records); err != nil {
			fmt.Fprintf(os.Stderr, "Error writing parquet: %v\n", err)
			os.Exit(1)
		}
		fmt.Fprintf(os.Stderr, "Successfully wrote %d records to features.parquet\n", len(records))
	} else {
		fmt.Fprintf(os.Stderr, "No records to write\n")
	}
}

func writeParquet(records []JerkRecord) error {
	fw, err := local.NewLocalFileWriter("features.parquet")
	if err != nil {
		return fmt.Errorf("failed to create file: %w", err)
	}
	defer fw.Close()

	pw, err := writer.NewParquetWriter(fw, new(JerkRecord), 4)
	if err != nil {
		return fmt.Errorf("failed to create parquet writer: %w", err)
	}
	defer pw.WriteStop()

	for _, record := range records {
		if err := pw.Write(record); err != nil {
			return fmt.Errorf("failed to write record: %w", err)
		}
	}

	return nil
}
