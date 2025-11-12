import pretty_midi
from pydub import AudioSegment
import os
import librosa
import soundfile as sf

# ------------------ CONFIG ------------------
MIDI_FILE = "song.mid"
OUTPUT_FILE = "output.wav"
TAIL_MS = 50  # extra tail after note ends
ENABLE_PITCH_SHIFT = True  # set False if not needed

# Track -> audio clip + reference pitch + base volume multiplier
TRACK_MAP = {
    0: {"clip": "guitar.wav", "REF_PITCH": 45, "BASE_VOLUME": 1},
    1: {"clip": "guitar.wav", "REF_PITCH": 55, "BASE_VOLUME": 1},
    2: {"clip": "dist.wav", "REF_PITCH": 60, "BASE_VOLUME": 1},
    3: {"clip": "dist.wav", "REF_PITCH": 55, "BASE_VOLUME": 1},
    4: {"clip": "bass.wav", "REF_PITCH": 40, "BASE_VOLUME": 1},
    5: {"clip": "drum.wav", "REF_PITCH": 64, "BASE_VOLUME": 0.75}
}
# --------------------------------------------

midi = pretty_midi.PrettyMIDI(MIDI_FILE)
output = AudioSegment.silent(duration=int(midi.get_end_time() * 1000))
clip_cache = {}  # (clip_file, pitch) -> AudioSegment

def load_and_pitch_clip(track_number, pitch):
    """Load clip and pitch-shift if needed (melodic tracks only)."""
    clip_file = TRACK_MAP[track_number]["clip"]
    key = (clip_file, pitch)
    if key in clip_cache:
        return clip_cache[key]

    if ENABLE_PITCH_SHIFT:
        REF_PITCH = TRACK_MAP[track_number]["REF_PITCH"]
        n_steps = (pitch - REF_PITCH) * 0.5
        y, sr = librosa.load(clip_file, sr=None)
        y_shifted = librosa.effects.pitch_shift(y=y, sr=sr, n_steps=n_steps)
        temp_file = f"temp_shifted_{os.path.basename(clip_file).replace('.','_')}_{pitch}.wav"
        sf.write(temp_file, y_shifted, sr)
        clip = AudioSegment.from_file(temp_file)
    else:
        clip = AudioSegment.from_file(clip_file)

    clip_cache[key] = clip
    return clip

# Process all notes
for track_index, instrument in enumerate(midi.instruments):
    print(f"Processing Track {track_index}, program={instrument.program}, drum={instrument.is_drum}")
    base_volume = TRACK_MAP[track_index]["BASE_VOLUME"]

    for note in instrument.notes:
        if instrument.is_drum:
            clip_file = TRACK_MAP[track_index]["clip"]
            clip = AudioSegment.from_file(clip_file)
        else:
            clip = load_and_pitch_clip(track_index, note.pitch)

        # Apply per-track volume (constant for all notes)
        if base_volume != 1:
            clip = clip + (20 * (base_volume - 1))  # rough linear→dB scale

        # Trim clip for melodic notes
        note_duration_ms = int((note.end - note.start) * 1000)
        clip_trimmed = clip if instrument.is_drum else clip[:note_duration_ms + TAIL_MS]

        start_ms = int(note.start * 1000)
        output = output.overlay(clip_trimmed, position=start_ms)

# Export
output.export(OUTPUT_FILE, format="wav")
print(f"Done! Output saved to {OUTPUT_FILE}")
