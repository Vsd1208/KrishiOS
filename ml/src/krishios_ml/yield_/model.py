"""B5: the shared multi-crop yield model (Phase 10).

Temporal encoder (GRU over dekads of weather and NDVI, with availability masks), static encoder
(yield history and season-level anomalies, with missingness flags), and embeddings for crop,
season token, state and forecast lead. There is no district embedding, so the model can serve
districts it never saw. It predicts ``ratio = yield / hist_mean`` as an offset from 1.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import torch
from torch import nn

from krishios_ml.yield_.sequences import DEKAD_DAYS, DEKADS, cutoff_day

SEQ_CHANNELS = 9  # 5 weather + 2 NDVI + 2 availability masks


def assemble(weather: torch.Tensor, ndvi: torch.Tensor, pub: torch.Tensor, lead: torch.Tensor,
             stats: dict[str, torch.Tensor]) -> torch.Tensor:
    """The forecast-time view: values not available at the cutoff become 0 with mask 0, so they
    cannot influence the model."""
    cutoff = cutoff_day(0) + lead
    steps = torch.arange(DEKADS, device=weather.device)[None]
    seen = (steps + 1) * DEKAD_DAYS <= cutoff[:, None]
    w_ok = seen & torch.isfinite(weather).all(-1)
    n_ok = (pub < cutoff[:, None]) & torch.isfinite(ndvi).all(-1)
    w = torch.where(w_ok[..., None], (weather - stats["w_mu"]) / stats["w_sd"],
                    torch.zeros_like(weather))
    n = torch.where(n_ok[..., None], (ndvi - stats["n_mu"]) / stats["n_sd"],
                    torch.zeros_like(ndvi))
    return torch.cat([w, n, w_ok[..., None].float(), n_ok[..., None].float()], dim=-1)


@dataclass(frozen=True)
class ModelConfig:
    n_static: int
    n_crops: int
    n_seasons: int
    n_states: int
    n_leads: int = 4
    hidden: int = 96
    dropout: float = 0.1


class YieldModel(nn.Module):
    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.config = asdict(cfg)
        h = cfg.hidden
        self.temporal = nn.GRU(SEQ_CHANNELS, h, batch_first=True)
        self.static = nn.Sequential(nn.Linear(cfg.n_static, h), nn.GELU(), nn.Dropout(cfg.dropout),
                                    nn.Linear(h, h), nn.GELU())
        self.crop = nn.Embedding(cfg.n_crops, 32)
        self.season = nn.Embedding(cfg.n_seasons, 8)
        self.state = nn.Embedding(cfg.n_states, 16)
        self.lead = nn.Embedding(cfg.n_leads, 8)
        self.drop = nn.Dropout(cfg.dropout)
        self.head = nn.Sequential(nn.Linear(2 * h + 64, 2 * h), nn.GELU(),
                                  nn.Dropout(cfg.dropout), nn.Linear(2 * h, h), nn.GELU(),
                                  nn.Linear(h, 1))

    def encode_sequence(self, seq: torch.Tensor) -> torch.Tensor:
        out, _ = self.temporal(seq)
        present = (seq[..., 7:9].sum(-1) > 0)[..., None].float()
        return (out * present).sum(1) / present.sum(1).clamp_min(1.0)

    def forward(self, seq, static, crop, season, state, lead_idx) -> torch.Tensor:
        z = torch.cat([self.encode_sequence(seq), self.static(static), self.crop(crop),
                       self.season(season), self.state(state), self.lead(lead_idx)], dim=-1)
        return 1.0 + self.head(self.drop(z)).squeeze(-1)
