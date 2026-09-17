"""Adds counterexamples for verified neutral error types to the v5 full training recipe.

Test/audit sentences never enter training. The new candidate model should
only be promoted to production if it passes the short-review, TRSAv1
held-out, and independent counterexample-set evaluations together.
"""

from finetune3 import main as tam_egitim
from hedefli_notr_karsi_ornekler import egitim_ornekleri


if __name__ == "__main__":
    tam_egitim(
        ek_hedefli_ornekler=egitim_ornekleri(),
        cikti_dizini="./duygu_finetuned_v6_full",
        gecici_dizin="./_egitim_gecici_v6",
    )
