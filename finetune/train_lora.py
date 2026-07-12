#!/usr/bin/env python3
"""LoRA fine-tune Qwen2.5-Coder-3B on the getdebug-edge review dataset.

Runs on the contest's free GPU (Udutech, ~5 hours) — a single T4/L4/A100 is
plenty for a 3B LoRA. Uses Unsloth for speed and low VRAM. This script is
meant to run in the GPU environment (Colab/Udutech), NOT on the laptop.

Pipeline (see finetune/README.md for the full runbook):
    1. python3 finetune/build_dataset.py        # on laptop: make train.jsonl
    2. upload train.jsonl to the GPU box
    3. python3 finetune/train_lora.py           # on GPU: trains + exports GGUF
    4. download the q4_k_m.gguf, bake persona, re-run eval, compare

Install on the GPU box:
    pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
    pip install --no-deps trl peft accelerate bitsandbytes
"""
import os

MAX_SEQ_LEN = 3072                 # matches the agent's --ctx-size
BASE = "unsloth/Qwen2.5-Coder-3B-Instruct"
DATA = os.environ.get("TRAIN_JSONL", "train.jsonl")
OUT_DIR = "getdebug-edge-3b-lora"
GGUF_QUANT = "q4_k_m"              # the submission quant


def main() -> None:
    from unsloth import FastLanguageModel
    from unsloth.chat_templates import get_chat_template
    from datasets import load_dataset
    from trl import SFTTrainer, SFTConfig

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE,
        max_seq_length=MAX_SEQ_LEN,
        load_in_4bit=True,            # QLoRA — fits a 3B comfortably on a T4
        dtype=None,
    )
    # Qwen2.5 uses ChatML; align the tokenizer template so training format ==
    # the format llama-server applies at inference.
    tokenizer = get_chat_template(tokenizer, chat_template="qwen-2.5")

    model = FastLanguageModel.get_peft_model(
        model,
        r=16,                         # LoRA rank — 16 is ample for this data size
        lora_alpha=16,
        lora_dropout=0.0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    def format_chat(batch):
        return {"text": [
            tokenizer.apply_chat_template(m, tokenize=False, add_generation_prompt=False)
            for m in batch["messages"]
        ]}

    ds = load_dataset("json", data_files=DATA, split="train").map(format_chat, batched=True)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=ds,
        args=SFTConfig(
            dataset_text_field="text",
            max_seq_length=MAX_SEQ_LEN,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            warmup_steps=5,
            num_train_epochs=3,       # small dataset -> a few epochs; watch for overfit
            learning_rate=2e-4,
            logging_steps=1,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="linear",
            seed=42,
            output_dir="outputs",
            report_to="none",
        ),
    )
    trainer.train()

    # Export a merged GGUF at the submission quant, ready for llama.cpp.
    model.save_pretrained_gguf(OUT_DIR, tokenizer, quantization_method=GGUF_QUANT)
    print(f"\nDone. GGUF written under {OUT_DIR}/ (quant {GGUF_QUANT}).")
    print("Next: bake persona (tools/bake_persona.py), then re-run eval/run_eval.py "
          "with --model pointing at the fine-tuned GGUF and compare to eval/baseline.json.")


if __name__ == "__main__":
    main()
