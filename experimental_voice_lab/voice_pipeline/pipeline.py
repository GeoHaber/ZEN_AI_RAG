# voice_pipeline/pipeline.py

import time

class VoicePipelineProfiler:
    def __init__(self):
        self.timings = {}

    def profile_stage(self, stage_name, func, *args, **kwargs):
        t0 = time.time()
        result = func(*args, **kwargs)
        self.timings[stage_name] = time.time() - t0
        return result

    def print_results(self):
        print("Profiling Results:")
        for stage, duration in self.timings.items():
            print(f"{stage.upper()}: {duration:.2f}s")

# Example usage (replace with real pipeline functions):
if __name__ == "__main__":
    profiler = VoicePipelineProfiler()
    profiler.profile_stage('vad', time.sleep, 0.5)
    profiler.profile_stage('stt', time.sleep, 1.0)
    profiler.profile_stage('llm', time.sleep, 4.0)
    profiler.profile_stage('tts', time.sleep, 1.5)
    profiler.print_results()
