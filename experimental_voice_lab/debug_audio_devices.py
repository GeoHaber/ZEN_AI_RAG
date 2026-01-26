
import sounddevice as sd

print("\n=== AUDIO DEVICE DIAGNOSTIC ===")
print(sd.query_devices())

print("\n=== INPUT DEVICES (Index Mapping) ===")
for i, dev in enumerate(sd.query_devices()):
    if dev['max_input_channels'] > 0:
        print(f"[{i}] {dev['name']} (API: {dev['hostapi']})")

print("\n=== OUTPUT DEVICES (Index Mapping) ===")
for i, dev in enumerate(sd.query_devices()):
    if dev['max_output_channels'] > 0:
        print(f"[{i}] {dev['name']} (API: {dev['hostapi']})")
