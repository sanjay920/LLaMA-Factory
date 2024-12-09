#!/bin/bash

python scripts/llama_pro.py \
    --model_name_or_path meta-llama/Llama-3.2-1B-Instruct \
    --output_dir models/llama3.2-1b-instruct-pro \
    --num_expand 8
