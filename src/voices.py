"""Voice definitions for text-to-speech conversion."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Union

from .config import KOKORO_PATHS
from .helpers import logger

# Language code mappings
LANG_CODES = {
    "a": "American English",
    "b": "British English",
    "e": "Spanish",
    "f": "French",
    "h": "Hindi",
    "i": "Italian",
    "p": "Brazilian Portuguese",
    "j": "Japanese",
    "z": "Mandarin Chinese",
}

ALIASES = {
    "en-us": "a",
    "en-gb": "b",
    "es": "e",
    "fr-fr": "f",
    "hi": "h",
    "it": "i",
    "pt-br": "p",
    "ja": "j",
    "zh": "z",
}


@dataclass
class VoiceInfo:
    """Information about a voice."""

    name: str  # Internal name used by the TTS system
    sha256: str  # SHA256 hash of the voice model
    gender: str  # "F" or "M"
    lang_code: str  # Single-letter language code (a, b, e, f, h, i, p, j, z)
    quality_grade: Optional[str] = None  # Overall quality grade (A-F)
    target_quality: Optional[str] = None  # Target quality grade (A-F)
    training_duration: Optional[str] = None  # Training duration category
    traits: Optional[str] = None  # Emoji traits
    cc_by: Optional[str] = None  # Attribution if under CC BY license
    local_path: Optional[str] = None  # Local path to the voice model


class Voice(Enum):
    """Available voices for text-to-speech conversion."""

    # American English Voices
    AF_HEART = VoiceInfo("af_heart", "0ab5709b", "F", "a", "A", None, None, "❤️")
    AF_ALLOY = VoiceInfo("af_alloy", "6d877149", "F", "a", "C", "B", "MM minutes")
    AF_AOEDE = VoiceInfo("af_aoede", "c03bd1a4", "F", "a", "C+", "B", "H hours")
    AF_BELLA = VoiceInfo("af_bella", "8cb64e02", "F", "a", "A-", "A", "HH hours", "🔥")
    AF_JESSICA = VoiceInfo("af_jessica", "cdfdccb8", "F", "a", "D", "C", "MM minutes")
    AF_KORE = VoiceInfo("af_kore", "8bfbc512", "F", "a", "C+", "B", "H hours")
    AF_NICOLE = VoiceInfo(
        "af_nicole", "c5561808", "F", "a", "B-", "B", "HH hours", "🎧"
    )
    AF_NOVA = VoiceInfo("af_nova", "e0233676", "F", "a", "C", "B", "MM minutes")
    AF_RIVER = VoiceInfo("af_river", "e149459b", "F", "a", "D", "C", "MM minutes")
    AF_SARAH = VoiceInfo("af_sarah", "49bd364e", "F", "a", "C+", "B", "H hours")
    AF_SKY = VoiceInfo("af_sky", "c799548a", "F", "a", "C-", "B", "M minutes")
    AM_ADAM = VoiceInfo("am_adam", "ced7e284", "M", "a", "F+", "D", "H hours")
    AM_ECHO = VoiceInfo("am_echo", "8bcfdc85", "M", "a", "D", "C", "MM minutes")
    AM_ERIC = VoiceInfo("am_eric", "ada66f0e", "M", "a", "D", "C", "MM minutes")
    AM_FENRIR = VoiceInfo("am_fenrir", "98e507ec", "M", "a", "C+", "B", "H hours")
    AM_LIAM = VoiceInfo("am_liam", "c8255075", "M", "a", "D", "C", "MM minutes")
    AM_MICHAEL = VoiceInfo("am_michael", "9a443b79", "M", "a", "C+", "B", "H hours")
    AM_ONYX = VoiceInfo("am_onyx", "e8452be1", "M", "a", "D", "C", "MM minutes")
    AM_PUCK = VoiceInfo("am_puck", "dd1d8973", "M", "a", "C+", "B", "H hours")
    AM_SANTA = VoiceInfo("am_santa", "7f2f7582", "M", "a", "D-", "C", "M minutes")

    # British English Voices
    BF_ALICE = VoiceInfo("bf_alice", "d292651b", "F", "b", "D", "C", "MM minutes")
    BF_EMMA = VoiceInfo("bf_emma", "d0a423de", "F", "b", "B-", "B", "HH hours")
    BF_ISABELLA = VoiceInfo("bf_isabella", "cdd4c370", "F", "b", "C", "B", "MM minutes")
    BF_LILY = VoiceInfo("bf_lily", "6e09c2e4", "F", "b", "D", "C", "MM minutes")
    BM_DANIEL = VoiceInfo("bm_daniel", "fc3fce4e", "M", "b", "D", "C", "MM minutes")
    BM_FABLE = VoiceInfo("bm_fable", "d44935f3", "M", "b", "C", "B", "MM minutes")
    BM_GEORGE = VoiceInfo("bm_george", "f1bc8122", "M", "b", "C", "B", "MM minutes")
    BM_LEWIS = VoiceInfo("bm_lewis", "b5204750", "M", "b", "D+", "C", "H hours")

    # Japanese Voices
    JF_ALPHA = VoiceInfo("jf_alpha", "1bf4c9dc", "F", "j", "C+", "B", "H hours")
    JF_GONGITSUNE = VoiceInfo(
        "jf_gongitsune",
        "1b171917",
        "F",
        "j",
        "C",
        "B",
        "MM minutes",
        None,
        "gongitsune",
    )
    JF_NEZUMI = VoiceInfo(
        "jf_nezumi",
        "d83f007a",
        "F",
        "j",
        "C-",
        "B",
        "M minutes",
        None,
        "nezuminoyomeiri",
    )
    JF_TEBUKURO = VoiceInfo(
        "jf_tebukuro",
        "0d691790",
        "F",
        "j",
        "C",
        "B",
        "MM minutes",
        None,
        "tebukurowokaini",
    )
    JM_KUMO = VoiceInfo(
        "jm_kumo", "98340afd", "M", "j", "C-", "B", "M minutes", None, "kumonoito"
    )

    # Mandarin Chinese Voices
    ZF_XIAOBEI = VoiceInfo("zf_xiaobei", "9b76be63", "F", "z", "D", "C", "MM minutes")
    ZF_XIAONI = VoiceInfo("zf_xiaoni", "95b49f16", "F", "z", "D", "C", "MM minutes")
    ZF_XIAOXIAO = VoiceInfo("zf_xiaoxiao", "cfaf6f2d", "F", "z", "D", "C", "MM minutes")
    ZF_XIAOYI = VoiceInfo("zf_xiaoyi", "b5235dba", "F", "z", "D", "C", "MM minutes")
    ZM_YUNJIAN = VoiceInfo("zm_yunjian", "76cbf8ba", "M", "z", "D", "C", "MM minutes")
    ZM_YUNXI = VoiceInfo("zm_yunxi", "dbe6e1ce", "M", "z", "D", "C", "MM minutes")
    ZM_YUNXIA = VoiceInfo("zm_yunxia", "bb2b03b0", "M", "z", "D", "C", "MM minutes")
    ZM_YUNYANG = VoiceInfo("zm_yunyang", "5238ac22", "M", "z", "D", "C", "MM minutes")

    # Spanish Voices
    EF_DORA = VoiceInfo("ef_dora", "d9d69b0f", "F", "e")
    EM_ALEX = VoiceInfo("em_alex", "5eac53f7", "M", "e")
    EM_SANTA = VoiceInfo("em_santa", "aa8620cb", "M", "e")

    # French Voices
    FF_SIWIS = VoiceInfo(
        "ff_siwis", "8073bf2d", "F", "f", "B-", "B", "<11 hours", None, "SIWIS"
    )

    # Hindi Voices
    HF_ALPHA = VoiceInfo("hf_alpha", "06906fe0", "F", "h", "C", "B", "MM minutes")
    HF_BETA = VoiceInfo("hf_beta", "63c0a1a6", "F", "h", "C", "B", "MM minutes")
    HM_OMEGA = VoiceInfo("hm_omega", "b55f02a8", "M", "h", "C", "B", "MM minutes")
    HM_PSI = VoiceInfo("hm_psi", "2f0f055c", "M", "h", "C", "B", "MM minutes")

    # Italian Voices
    IF_SARA = VoiceInfo("if_sara", "6c0b253b", "F", "i", "C", "B", "MM minutes")
    IM_NICOLA = VoiceInfo("im_nicola", "234ed066", "M", "i", "C", "B", "MM minutes")

    # Brazilian Portuguese Voices
    PF_DORA = VoiceInfo("pf_dora", "07e4ff98", "F", "p")
    PM_ALEX = VoiceInfo("pm_alex", "cf0ba8c5", "M", "p")
    PM_SANTA = VoiceInfo("pm_santa", "d4210316", "M", "p")

    @property
    def info(self) -> VoiceInfo:
        """Get the voice information."""
        return self.value

    @property
    def name(self) -> str:
        """Get the voice name."""
        return self.value.name

    @property
    def sha256(self) -> str:
        """Get the voice model SHA256 hash."""
        return self.value.sha256

    @property
    def gender(self) -> str:
        """Get the voice gender (F/M)."""
        return self.value.gender

    @property
    def lang_code(self) -> str:
        """Get the voice language code."""
        return self.value.lang_code

    @property
    def local_path(self) -> str | None:
        """Get the voice language code."""
        return self.value.local_path

    @property
    def language(self) -> str:
        """Get the full language name or code."""
        return LANG_CODES[self.value.lang_code]

    @property
    def quality_grade(self) -> Optional[str]:
        """Get the voice quality grade."""
        return self.value.quality_grade

    @property
    def is_female(self) -> bool:
        """Check if the voice is female."""
        return self.value.gender == "F"

    @property
    def is_male(self) -> bool:
        """Check if the voice is male."""
        return self.value.gender == "M"

    def set_path(self, voice_path: Union[str, Path]) -> bool:
        """Set local path, if it exists."""
        if Path(voice_path).is_file():
            self.value.local_path = str(voice_path)
            return True
        return False

    @classmethod
    def get_by_name(cls, name: str) -> "Voice":
        """Get a voice by its name.

        Args:
            name: The name of the voice to get.

        Returns:
            The voice enum value.

        Raises:
            ValueError: If no voice with the given name exists.
        """
        for voice in cls:
            if voice.name == name:
                local_path = Path(KOKORO_PATHS["voice_weights"]) / f"{name}.pt"
                if Path(local_path).is_file():
                    voice.value.local_path = str(local_path)
                return voice
        raise ValueError(f"No voice named '{name}'")

    @classmethod
    def list_voices(
        cls,
        gender: Optional[str] = None,
        min_grade: Optional[str] = None,
        lang_code: Optional[str] = None,
    ) -> list["Voice"]:
        """List available voices with optional filtering.

        Args:
            gender: Optional filter by gender ("F" or "M")
            min_grade: Optional minimum quality grade (A-F)
            lang_code: Optional language code,
                can be alias like 'en-us' or internal code like 'a'

        Returns:
            List of voices matching the criteria.
        """
        voices = list(cls)

        if gender:
            voices = [v for v in voices if v.gender == gender.upper()]

        if min_grade:
            # Convert grade to numeric value (A=4, B=3, etc.)
            def grade_to_num(grade: Optional[str]) -> float:
                if not grade:
                    return -1
                base = 4.0 - (ord(grade[0]) - ord("A"))
                modifier = grade[1] if len(grade) > 1 else ""
                if modifier == "+":
                    base += 0.3
                elif modifier == "-":
                    base -= 0.3
                return base

            min_num = grade_to_num(min_grade)
            voices = [v for v in voices if grade_to_num(v.quality_grade) >= min_num]

        if lang_code:
            # Convert alias to internal code if needed
            internal_code = ALIASES.get(lang_code, lang_code)
            voices = [v for v in voices if v.lang_code == internal_code]

        return voices


if Path(KOKORO_PATHS["voice_weights"]).exists():
    logger.debug("weight path exists")
    for file in Path(KOKORO_PATHS["voice_weights"]).glob("*.pt"):
        logger.debug(f"found voice file: {file}")
        Voice.get_by_name(file.stem).set_path(file)
