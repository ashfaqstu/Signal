"""Applied features. All three are the same align + temporal-reduce engine."""

from .highlight import (DETECTORS, adaptive_threshold, bounding_boxes,
                        change_score, clean_mask, highlight,
                        highlight_sequence, outline_of)
from .pipeline import (PRESET_PIPELINES, STEPS, Pipeline, PipelineResult)
from .removal import (background_and_foreground, compare_temporal_filters,
                      most_disturbed_pixel, pixel_timeseries,
                      remove_moving_objects, running_median)
from .stacking import (align_frames, align_reference_to_output,
                       common_valid_mask, compare_reducers, stack,
                       stack_report)
from .temporal import REDUCERS, reduce, theoretical_gain_db
