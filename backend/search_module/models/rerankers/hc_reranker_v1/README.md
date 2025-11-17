---
tags:
- sentence-transformers
- cross-encoder
- reranker
- generated_from_trainer
- dataset_size:51183
- loss:BinaryCrossEntropyLoss
base_model: cross-encoder/ms-marco-MiniLM-L6-v2
pipeline_tag: text-ranking
library_name: sentence-transformers
metrics:
- accuracy
- accuracy_threshold
- f1
- f1_threshold
- precision
- recall
- average_precision
model-index:
- name: CrossEncoder based on cross-encoder/ms-marco-MiniLM-L6-v2
  results:
  - task:
      type: cross-encoder-binary-classification
      name: Cross Encoder Binary Classification
    dataset:
      name: val
      type: val
    metrics:
    - type: accuracy
      value: 0.9984177215189873
      name: Accuracy
    - type: accuracy_threshold
      value: 2.5698390007019043
      name: Accuracy Threshold
    - type: f1
      value: 0.923076923076923
      name: F1
    - type: f1_threshold
      value: 2.5698390007019043
      name: F1 Threshold
    - type: precision
      value: 1.0
      name: Precision
    - type: recall
      value: 0.8571428571428571
      name: Recall
    - type: average_precision
      value: 0.9523189180704927
      name: Average Precision
---

# CrossEncoder based on cross-encoder/ms-marco-MiniLM-L6-v2

This is a [Cross Encoder](https://www.sbert.net/docs/cross_encoder/usage/usage.html) model finetuned from [cross-encoder/ms-marco-MiniLM-L6-v2](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2) using the [sentence-transformers](https://www.SBERT.net) library. It computes scores for pairs of texts, which can be used for text reranking and semantic search.

## Model Details

### Model Description
- **Model Type:** Cross Encoder
- **Base model:** [cross-encoder/ms-marco-MiniLM-L6-v2](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2) <!-- at revision c5ee24cb16019beea0893ab7796b1df96625c6b8 -->
- **Maximum Sequence Length:** 512 tokens
- **Number of Output Labels:** 1 label
<!-- - **Training Dataset:** Unknown -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Documentation:** [Sentence Transformers Documentation](https://sbert.net)
- **Documentation:** [Cross Encoder Documentation](https://www.sbert.net/docs/cross_encoder/usage/usage.html)
- **Repository:** [Sentence Transformers on GitHub](https://github.com/UKPLab/sentence-transformers)
- **Hugging Face:** [Cross Encoders on Hugging Face](https://huggingface.co/models?library=sentence-transformers&other=cross-encoder)

## Usage

### Direct Usage (Sentence Transformers)

First install the Sentence Transformers library:

```bash
pip install -U sentence-transformers
```

Then you can load this model and run inference.
```python
from sentence_transformers import CrossEncoder

# Download from the 🤗 Hub
model = CrossEncoder("cross_encoder_model_id")
# Get scores for pairs of texts
pairs = [
    ['Query: Dispute over that applicants advocate before High Court', 'Candidate: Title: Natover International Private Limited etc VS Bank Alfalah Limited | Number: E.F.A. 1/2011 Banking (DB) | Court: Islamabad High Court | Status: Decided | Bench: Honourable Mr. Justice Mohsin Akhtar Kayani, Justice Ms. Lubna Saleem Pervez'],
    ['Query: Uneza Jawed vs FOP through Secretary Revenue Division W.P. 1/2025 Tax & Banking Tax (SB)', 'Candidate: Title: Muhammad Shoaib Shaheen VS Returning officer | Number: EA 1/2024 (SB) | Court: Islamabad High Court | Status: Decided | Bench: Honourable Mr. Justice Arbab Muhammad Tahir | Summary: Case Number: EA 1/2024 (SB) | Title: Muhammad Shoaib Shaheen vs Returning officer | Parties: Muhammad Shoaib Shaheen vs Returning officer | Status: Decided | Subjects: Administrative Law, Banking & Finance, Constitutional & Writs, Education, Election Matters, Labour & Service, Property & Land, Taxation & Revenue | Sections: Article 62, Article 62(1), Authority, Constitutional, Default | Abstract: - 22- Tersely, relevant facts leading to filing of the subject appeals are that nomination papers of the appellant Muhammad Shoaib Shaheen for contesting General Elections Islamabad were rejected by the Returning Officer vide NA-46 Islamabad “It is clear that Mr. Shoaib Shaheen is defaulter of property Tax under the constitutional and statutory framework duly attested and interpreted by the Honorable Superior Courts. Muhammad Shoaib Shaheen is a defaulter having liability towards Capital Development Authority/MCI while filing nomination papers. | Keywords: article 62, article 62(1), authority, constitutional, default, discretion | Summary Snippet: - 22- Tersely, relevant facts leading to filing of the subject appeals are that nomination papers of the appellant Muhammad Shoaib Shaheen for contesting General Elections Islamabad were rejected by the Returning Officer vide NA-46 Islamabad “It is clear that Mr. Shoaib Shaheen is defaulter of property Tax under the constitutional and statutory framework duly attested and interpreted by the Honora... | Abstract: - 22- Tersely, relevant facts leading to filing of the subject appeals are that nomination papers of the appellant Muhammad Shoaib Shaheen for contesting General Elections Islamabad were rejected by the Returning Officer vide NA-46 Islamabad “It is clear that Mr. Shoaib Shaheen is defaulter of property Tax under the constitutional and statutory framework duly attested and interpreted by the Honorable Superior Courts. Muhammad Shoaib Shaheen is a defaulter having liability towards Capital Development Authority/MCI while filing nomination papers. | Subjects: administrative, banking, constitutional, education, election, labour, property, tax | Sections: Article 62, Article 62(1), Authority, Constitutional, Default, Discretion, Election, Exam, Nomination Papers, Property, Returning Officer, Rule 18(3), Section 173, Section 62(9), Tax, Termination | Abstract sentences: - 22- Tersely, relevant facts leading to filing of the subject appeals are that nomination papers of the appellant Muhammad Shoaib Shaheen for contesting General Elections Islamabad were rejected by the Returning Officer vide NA-46 Islamabad “It is clear that Mr. Shoaib Shaheen is defaulter of property Tax under the constitutional and statutory framework duly attested and interpreted by the Honorable Superior Courts. Muhammad Shoaib Shaheen is a defaulter having liability towards Capital Development Authority/MCI while filing nomination papers.'],
    ['Query: Explain the judgment in Naseer Chohan vs IDK Ventures', 'Candidate: Title: Frontier Holding VS Petroleum Exploration | Number: Enfrc. Pet. 2/2025 (SB) | Court: Islamabad High Court | Status: Pending | Bench: Honourable Mr. Justice Muhammad Asif'],
    ['Query: Which case discusses 4. Learned counsel for the petitioner contended that the parties and subject matter of both the applications are same, t', 'Candidate: Title: Mst. Neelam Bibi VS The State | Number: Crl. Misc. 5/2025 Bail After Arrest (SB) | Court: Islamabad High Court | Status: Decided | Bench: Honourable Ms. Justice Saman Rafat Imtiaz | Summary: Case Number: Crl. Misc. 5/2025 Bail After Arrest (SB) | Title: Mst. Neelam Bibi vs The State | Parties: Mst. Neelam Bibi vs The State | Status: Decided'],
    ['Query: F.A.O. 3/2024 Against Order (SB) appellant counsel', 'Candidate: Title: Ghulam Asghar kiyani etc VS Pervaiz Sadiq Kiyani | Number: R.S.A. 1/2024 Against Judgement & Decree (SB) | Court: Islamabad High Court | Status: Pending | Bench: Honourable Mr. Justice Muhammad Azam Khan'],
]
scores = model.predict(pairs)
print(scores.shape)
# (5,)

# Or rank different texts based on similarity to a single text
ranks = model.rank(
    'Query: Dispute over that applicants advocate before High Court',
    [
        'Candidate: Title: Natover International Private Limited etc VS Bank Alfalah Limited | Number: E.F.A. 1/2011 Banking (DB) | Court: Islamabad High Court | Status: Decided | Bench: Honourable Mr. Justice Mohsin Akhtar Kayani, Justice Ms. Lubna Saleem Pervez',
        'Candidate: Title: Muhammad Shoaib Shaheen VS Returning officer | Number: EA 1/2024 (SB) | Court: Islamabad High Court | Status: Decided | Bench: Honourable Mr. Justice Arbab Muhammad Tahir | Summary: Case Number: EA 1/2024 (SB) | Title: Muhammad Shoaib Shaheen vs Returning officer | Parties: Muhammad Shoaib Shaheen vs Returning officer | Status: Decided | Subjects: Administrative Law, Banking & Finance, Constitutional & Writs, Education, Election Matters, Labour & Service, Property & Land, Taxation & Revenue | Sections: Article 62, Article 62(1), Authority, Constitutional, Default | Abstract: - 22- Tersely, relevant facts leading to filing of the subject appeals are that nomination papers of the appellant Muhammad Shoaib Shaheen for contesting General Elections Islamabad were rejected by the Returning Officer vide NA-46 Islamabad “It is clear that Mr. Shoaib Shaheen is defaulter of property Tax under the constitutional and statutory framework duly attested and interpreted by the Honorable Superior Courts. Muhammad Shoaib Shaheen is a defaulter having liability towards Capital Development Authority/MCI while filing nomination papers. | Keywords: article 62, article 62(1), authority, constitutional, default, discretion | Summary Snippet: - 22- Tersely, relevant facts leading to filing of the subject appeals are that nomination papers of the appellant Muhammad Shoaib Shaheen for contesting General Elections Islamabad were rejected by the Returning Officer vide NA-46 Islamabad “It is clear that Mr. Shoaib Shaheen is defaulter of property Tax under the constitutional and statutory framework duly attested and interpreted by the Honora... | Abstract: - 22- Tersely, relevant facts leading to filing of the subject appeals are that nomination papers of the appellant Muhammad Shoaib Shaheen for contesting General Elections Islamabad were rejected by the Returning Officer vide NA-46 Islamabad “It is clear that Mr. Shoaib Shaheen is defaulter of property Tax under the constitutional and statutory framework duly attested and interpreted by the Honorable Superior Courts. Muhammad Shoaib Shaheen is a defaulter having liability towards Capital Development Authority/MCI while filing nomination papers. | Subjects: administrative, banking, constitutional, education, election, labour, property, tax | Sections: Article 62, Article 62(1), Authority, Constitutional, Default, Discretion, Election, Exam, Nomination Papers, Property, Returning Officer, Rule 18(3), Section 173, Section 62(9), Tax, Termination | Abstract sentences: - 22- Tersely, relevant facts leading to filing of the subject appeals are that nomination papers of the appellant Muhammad Shoaib Shaheen for contesting General Elections Islamabad were rejected by the Returning Officer vide NA-46 Islamabad “It is clear that Mr. Shoaib Shaheen is defaulter of property Tax under the constitutional and statutory framework duly attested and interpreted by the Honorable Superior Courts. Muhammad Shoaib Shaheen is a defaulter having liability towards Capital Development Authority/MCI while filing nomination papers.',
        'Candidate: Title: Frontier Holding VS Petroleum Exploration | Number: Enfrc. Pet. 2/2025 (SB) | Court: Islamabad High Court | Status: Pending | Bench: Honourable Mr. Justice Muhammad Asif',
        'Candidate: Title: Mst. Neelam Bibi VS The State | Number: Crl. Misc. 5/2025 Bail After Arrest (SB) | Court: Islamabad High Court | Status: Decided | Bench: Honourable Ms. Justice Saman Rafat Imtiaz | Summary: Case Number: Crl. Misc. 5/2025 Bail After Arrest (SB) | Title: Mst. Neelam Bibi vs The State | Parties: Mst. Neelam Bibi vs The State | Status: Decided',
        'Candidate: Title: Ghulam Asghar kiyani etc VS Pervaiz Sadiq Kiyani | Number: R.S.A. 1/2024 Against Judgement & Decree (SB) | Court: Islamabad High Court | Status: Pending | Bench: Honourable Mr. Justice Muhammad Azam Khan',
    ]
)
# [{'corpus_id': ..., 'score': ...}, {'corpus_id': ..., 'score': ...}, ...]
```

<!--
### Direct Usage (Transformers)

<details><summary>Click to see the direct usage in Transformers</summary>

</details>
-->

<!--
### Downstream Usage (Sentence Transformers)

You can finetune this model on your own dataset.

<details><summary>Click to expand</summary>

</details>
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

## Evaluation

### Metrics

#### Cross Encoder Binary Classification

* Dataset: `val`
* Evaluated with [<code>CEBinaryClassificationEvaluator</code>](https://sbert.net/docs/package_reference/cross_encoder/evaluation.html#sentence_transformers.cross_encoder.evaluation.CEBinaryClassificationEvaluator)

| Metric                | Value      |
|:----------------------|:-----------|
| accuracy              | 0.9984     |
| accuracy_threshold    | 2.5698     |
| f1                    | 0.9231     |
| f1_threshold          | 2.5698     |
| precision             | 1.0        |
| recall                | 0.8571     |
| **average_precision** | **0.9523** |

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Dataset

#### Unnamed Dataset

* Size: 51,183 training samples
* Columns: <code>sentence_0</code>, <code>sentence_1</code>, and <code>label</code>
* Approximate statistics based on the first 1000 samples:
  |         | sentence_0                                                                                      | sentence_1                                                                                          | label                                                          |
  |:--------|:------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------|:---------------------------------------------------------------|
  | type    | string                                                                                          | string                                                                                              | float                                                          |
  | details | <ul><li>min: 21 characters</li><li>mean: 73.64 characters</li><li>max: 173 characters</li></ul> | <ul><li>min: 136 characters</li><li>mean: 1056.85 characters</li><li>max: 3620 characters</li></ul> | <ul><li>min: 0.0</li><li>mean: 0.01</li><li>max: 1.0</li></ul> |
* Samples:
  | sentence_0                                                                                                   | sentence_1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | label            |
  |:-------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------|
  | <code>Query: Dispute over that applicants advocate before High Court</code>                                  | <code>Candidate: Title: Natover International Private Limited etc VS Bank Alfalah Limited | Number: E.F.A. 1/2011 Banking (DB) | Court: Islamabad High Court | Status: Decided | Bench: Honourable Mr. Justice Mohsin Akhtar Kayani, Justice Ms. Lubna Saleem Pervez</code>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | <code>0.0</code> |
  | <code>Query: Uneza Jawed vs FOP through Secretary Revenue Division W.P. 1/2025 Tax & Banking Tax (SB)</code> | <code>Candidate: Title: Muhammad Shoaib Shaheen VS Returning officer | Number: EA 1/2024 (SB) | Court: Islamabad High Court | Status: Decided | Bench: Honourable Mr. Justice Arbab Muhammad Tahir | Summary: Case Number: EA 1/2024 (SB) | Title: Muhammad Shoaib Shaheen vs Returning officer | Parties: Muhammad Shoaib Shaheen vs Returning officer | Status: Decided | Subjects: Administrative Law, Banking & Finance, Constitutional & Writs, Education, Election Matters, Labour & Service, Property & Land, Taxation & Revenue | Sections: Article 62, Article 62(1), Authority, Constitutional, Default | Abstract: - 22- Tersely, relevant facts leading to filing of the subject appeals are that nomination papers of the appellant Muhammad Shoaib Shaheen for contesting General Elections Islamabad were rejected by the Returning Officer vide NA-46 Islamabad “It is clear that Mr. Shoaib Shaheen is defaulter of property Tax under the constitutional and statutory framework duly attested and interpreted by the Honora...</code> | <code>0.0</code> |
  | <code>Query: Explain the judgment in Naseer Chohan vs IDK Ventures</code>                                    | <code>Candidate: Title: Frontier Holding VS Petroleum Exploration | Number: Enfrc. Pet. 2/2025 (SB) | Court: Islamabad High Court | Status: Pending | Bench: Honourable Mr. Justice Muhammad Asif</code>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | <code>0.0</code> |
* Loss: [<code>BinaryCrossEntropyLoss</code>](https://sbert.net/docs/package_reference/cross_encoder/losses.html#binarycrossentropyloss) with these parameters:
  ```json
  {
      "activation_fn": "torch.nn.modules.linear.Identity",
      "pos_weight": null
  }
  ```

### Training Hyperparameters
#### Non-Default Hyperparameters

- `eval_strategy`: steps
- `per_device_train_batch_size`: 16
- `per_device_eval_batch_size`: 16
- `num_train_epochs`: 1

#### All Hyperparameters
<details><summary>Click to expand</summary>

- `overwrite_output_dir`: False
- `do_predict`: False
- `eval_strategy`: steps
- `prediction_loss_only`: True
- `per_device_train_batch_size`: 16
- `per_device_eval_batch_size`: 16
- `per_gpu_train_batch_size`: None
- `per_gpu_eval_batch_size`: None
- `gradient_accumulation_steps`: 1
- `eval_accumulation_steps`: None
- `torch_empty_cache_steps`: None
- `learning_rate`: 5e-05
- `weight_decay`: 0.0
- `adam_beta1`: 0.9
- `adam_beta2`: 0.999
- `adam_epsilon`: 1e-08
- `max_grad_norm`: 1
- `num_train_epochs`: 1
- `max_steps`: -1
- `lr_scheduler_type`: linear
- `lr_scheduler_kwargs`: {}
- `warmup_ratio`: 0.0
- `warmup_steps`: 0
- `log_level`: passive
- `log_level_replica`: warning
- `log_on_each_node`: True
- `logging_nan_inf_filter`: True
- `save_safetensors`: True
- `save_on_each_node`: False
- `save_only_model`: False
- `restore_callback_states_from_checkpoint`: False
- `no_cuda`: False
- `use_cpu`: False
- `use_mps_device`: False
- `seed`: 42
- `data_seed`: None
- `jit_mode_eval`: False
- `use_ipex`: False
- `bf16`: False
- `fp16`: False
- `fp16_opt_level`: O1
- `half_precision_backend`: auto
- `bf16_full_eval`: False
- `fp16_full_eval`: False
- `tf32`: None
- `local_rank`: 0
- `ddp_backend`: None
- `tpu_num_cores`: None
- `tpu_metrics_debug`: False
- `debug`: []
- `dataloader_drop_last`: False
- `dataloader_num_workers`: 0
- `dataloader_prefetch_factor`: None
- `past_index`: -1
- `disable_tqdm`: False
- `remove_unused_columns`: True
- `label_names`: None
- `load_best_model_at_end`: False
- `ignore_data_skip`: False
- `fsdp`: []
- `fsdp_min_num_params`: 0
- `fsdp_config`: {'min_num_params': 0, 'xla': False, 'xla_fsdp_v2': False, 'xla_fsdp_grad_ckpt': False}
- `fsdp_transformer_layer_cls_to_wrap`: None
- `accelerator_config`: {'split_batches': False, 'dispatch_batches': None, 'even_batches': True, 'use_seedable_sampler': True, 'non_blocking': False, 'gradient_accumulation_kwargs': None}
- `deepspeed`: None
- `label_smoothing_factor`: 0.0
- `optim`: adamw_torch
- `optim_args`: None
- `adafactor`: False
- `group_by_length`: False
- `length_column_name`: length
- `ddp_find_unused_parameters`: None
- `ddp_bucket_cap_mb`: None
- `ddp_broadcast_buffers`: False
- `dataloader_pin_memory`: True
- `dataloader_persistent_workers`: False
- `skip_memory_metrics`: True
- `use_legacy_prediction_loop`: False
- `push_to_hub`: False
- `resume_from_checkpoint`: None
- `hub_model_id`: None
- `hub_strategy`: every_save
- `hub_private_repo`: None
- `hub_always_push`: False
- `hub_revision`: None
- `gradient_checkpointing`: False
- `gradient_checkpointing_kwargs`: None
- `include_inputs_for_metrics`: False
- `include_for_metrics`: []
- `eval_do_concat_batches`: True
- `fp16_backend`: auto
- `push_to_hub_model_id`: None
- `push_to_hub_organization`: None
- `mp_parameters`: 
- `auto_find_batch_size`: False
- `full_determinism`: False
- `torchdynamo`: None
- `ray_scope`: last
- `ddp_timeout`: 1800
- `torch_compile`: False
- `torch_compile_backend`: None
- `torch_compile_mode`: None
- `include_tokens_per_second`: False
- `include_num_input_tokens_seen`: False
- `neftune_noise_alpha`: None
- `optim_target_modules`: None
- `batch_eval_metrics`: False
- `eval_on_start`: False
- `use_liger_kernel`: False
- `liger_kernel_config`: None
- `eval_use_gather_object`: False
- `average_tokens_across_devices`: False
- `prompts`: None
- `batch_sampler`: batch_sampler
- `multi_dataset_batch_sampler`: proportional
- `router_mapping`: {}
- `learning_rate_mapping`: {}

</details>

### Training Logs
| Epoch  | Step | Training Loss | val_average_precision |
|:------:|:----:|:-------------:|:---------------------:|
| 0.1563 | 500  | 0.0393        | -                     |
| 0.3126 | 1000 | 0.0258        | -                     |
| 0.4689 | 1500 | 0.0162        | -                     |
| 0.6252 | 2000 | 0.0136        | -                     |
| 0.7815 | 2500 | 0.0153        | -                     |
| 0.9378 | 3000 | 0.0112        | -                     |
| 1.0    | 3199 | -             | 0.9523                |


### Framework Versions
- Python: 3.12.7
- Sentence Transformers: 5.0.0
- Transformers: 4.54.1
- PyTorch: 2.7.1+cpu
- Accelerate: 1.11.0
- Datasets: 4.4.1
- Tokenizers: 0.21.4

## Citation

### BibTeX

#### Sentence Transformers
```bibtex
@inproceedings{reimers-2019-sentence-bert,
    title = "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
    author = "Reimers, Nils and Gurevych, Iryna",
    booktitle = "Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing",
    month = "11",
    year = "2019",
    publisher = "Association for Computational Linguistics",
    url = "https://arxiv.org/abs/1908.10084",
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->