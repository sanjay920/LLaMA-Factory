#!/bin/bash

python scripts/llama_pro.py \
    --model_name_or_path microsoft/Phi-3.5-mini-instruct \
    --output_dir models/phi-3.5-mini-instruct-pro-16 \
    --num_expand 16
