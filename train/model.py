"""AfroXLMR-base with 8 yes/no heads (768 -> 8, sigmoid on the <s> token). PRESENT at p >= 0.5 (prereg section 7)."""
import torch
from torch import nn
from transformers import AutoModel

BASE = "Davlan/afro-xlmr-base"
HEADS = ["convulsions", "not_drink_feed", "vomits_everything", "sleepy_unconscious",
         "blood_stool", "cough_long", "diarrhoea_long", "fever_long"]
MAX_LEN = 256
THRESHOLD = 0.5


class SignModel(nn.Module):
    def __init__(self, base=BASE):
        super().__init__()
        self.encoder = AutoModel.from_pretrained(base)
        self.head = nn.Linear(self.encoder.config.hidden_size, len(HEADS))

    def forward(self, input_ids, attention_mask):
        h = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state[:, 0]
        return self.head(h)                       # logits; sigmoid gives p per head


class ProbModel(nn.Module):
    """Export wrapper: returns sigmoid probabilities."""

    def __init__(self, m):
        super().__init__()
        self.m = m

    def forward(self, input_ids, attention_mask):
        return torch.sigmoid(self.m(input_ids, attention_mask))
