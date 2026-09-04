#!/usr/bin/env python3
"""Génère les fichiers audio d'ancrage oral à partir de Orbis_Scripts_Audio.md.

Pour chacun des 8 blocs du document, produit deux MP3 :

  audio/blocN_pitch.mp3      le script PITCH, à écouter en boucle
  audio/blocN_objection.mp3  objection → silence pour répondre → réponse modèle

… puis deux playlists concaténées (playlist_pitch.mp3, playlist_objection.mp3).

Synthèse vocale : Piper (modèle neuronal VITS, 100 % hors ligne).
Encodage MP3 : ffmpeg.

Usage :
    python3 generate_audio.py                       # tout générer
    python3 generate_audio.py --voice fr-gilles-low # autre voix
    python3 generate_audio.py --pause 15            # silence de réponse plus long
    python3 generate_audio.py --blocs 1 3           # seulement certains blocs
    python3 generate_audio.py --samples             # échantillon des 4 voix
"""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "Orbis_Scripts_Audio.md"
VOICES_DIR = ROOT / "voices"
OUT_DIR = ROOT / "audio"

VOICE_RELEASE = "https://github.com/rhasspy/piper/releases/download/v0.0.2"
AVAILABLE_VOICES = {
    # nom local            : (archive de la release, description)
    "fr-siwis-medium": ("voice-fr-siwis-medium", "féminine, 22 kHz, qualité medium (défaut)"),
    "fr-gilles-low": ("voice-fr-gilles-low", "masculine, 16 kHz, qualité low"),
    "fr-siwis-low": ("voice-fr-siwis-low", "féminine, 16 kHz, qualité low"),
}
DEFAULT_VOICE = "fr-siwis-medium"

NUM_FR = {
    1: "un", 2: "deux", 3: "trois", 4: "quatre",
    5: "cinq", 6: "six", 7: "sept", 8: "huit",
}

# Sigles : espacés pour être épelés lettre à lettre par le moteur français.
ACRONYMS = {
    "P&L": "P et L",
    "COO": "C O O",
    "CFO": "C F O",
    "DRH": "D R H",
    "ESN": "E S N",
    "SLA": "S L A",
    "RPA": "R P A",
    "IA": "I A",
    "IT": "I T",
    "P&amp;L": "P et L",
}

# Repères parlés insérés dans la piste OBJECTION.
CUE_ANSWER = "À vous. Répondez à voix haute."
CUE_MODEL = "Réponse modèle."


# --------------------------------------------------------------------------- #
# Lecture du markdown
# --------------------------------------------------------------------------- #

@dataclass
class Bloc:
    number: int
    title: str
    pitch: list[str]          # paragraphes du pitch
    objection: list[str]      # paragraphes de l'objection (avant le silence)
    answer: list[str]         # paragraphes de la réponse modèle


def parse_source(path: Path) -> list[Bloc]:
    """Extrait les 8 blocs et leurs sections PITCH / OBJECTION du markdown."""
    text = path.read_text(encoding="utf-8")

    # On s'arrête avant la section d'instructions finale.
    cut = re.search(r"^# INSTRUCTIONS", text, flags=re.M)
    if cut:
        text = text[: cut.start()]

    blocs: list[Bloc] = []
    chunks = re.split(r"^## BLOC (\d+)\s*[—-]\s*(.+)$", text, flags=re.M)
    # chunks = [préambule, num, titre, corps, num, titre, corps, ...]
    for i in range(1, len(chunks), 3):
        number = int(chunks[i])
        title = chunks[i + 1].strip()
        body = chunks[i + 2]

        pitch_raw = _section(body, "PITCH")
        objection_raw = _section(body, "OBJECTION")
        if pitch_raw is None or objection_raw is None:
            raise SystemExit(f"BLOC {number} : section PITCH ou OBJECTION introuvable.")

        objection, answer = _split_objection(objection_raw, number)
        blocs.append(
            Bloc(
                number=number,
                title=title,
                pitch=paragraphs(pitch_raw),
                objection=objection,
                answer=answer,
            )
        )

    if not blocs:
        raise SystemExit("Aucun bloc trouvé dans le document source.")
    return blocs


def _section(body: str, name: str) -> str | None:
    """Renvoie le corps brut d'une sous-section `### NOM`."""
    match = re.search(
        rf"^### {name}\s*$(.*?)(?=^### |\Z)", body, flags=re.M | re.S
    )
    return match.group(1) if match else None


def _split_objection(raw: str, number: int) -> tuple[list[str], list[str]]:
    """Sépare la partie « objection » de la partie « réponse modèle »."""
    paras = paragraphs(raw)
    objection: list[str] = []
    answer: list[str] = []
    in_answer = False

    for para in paras:
        flat = strip_emphasis(para)
        # La consigne « [Répondez à voix haute…] » est remplacée par un vrai silence.
        if flat.startswith("[") and "voix haute" in flat:
            continue
        if re.match(r"^Réponse modèle\s*:?\s*$", flat):
            in_answer = True
            continue
        (answer if in_answer else objection).append(para)

    if not objection or not answer:
        raise SystemExit(f"BLOC {number} : structure de l'OBJECTION inattendue.")
    return objection, answer


def paragraphs(raw: str) -> list[str]:
    """Découpe un bloc markdown en paragraphes non vides, séparateurs exclus."""
    out = []
    for para in re.split(r"\n\s*\n", raw):
        para = " ".join(line.strip() for line in para.strip().splitlines()).strip()
        if not para or set(para) <= {"-", "*", "_"}:
            continue
        out.append(para)
    return out


# --------------------------------------------------------------------------- #
# Préparation du texte pour la synthèse
# --------------------------------------------------------------------------- #

def strip_emphasis(text: str) -> str:
    return re.sub(r"[*_`]", "", text).strip()


def to_speech(text: str) -> str:
    """Nettoie un paragraphe markdown pour qu'il soit *dit* correctement."""
    out = strip_emphasis(text)

    # Guillemets et crochets : purement typographiques à l'écrit.
    out = out.translate(str.maketrans("", "", "«»\"[]"))
    out = out.replace("’", "'")

    # Tiret cadratin : une respiration, pas un mot.
    out = re.sub(r"\s*[—–]\s*", ", ", out)

    # Sigles épelés lettre à lettre.
    for sigle, spoken in ACRONYMS.items():
        out = re.sub(rf"(?<![\w&]){re.escape(sigle)}(?![\w&])", spoken, out)

    out = re.sub(r"\s+", " ", out).strip()
    # Une phrase se termine par une ponctuation : le moteur y pose une pause.
    if out and out[-1] not in ".!?:;,":
        out += "."
    return out


def title_to_speech(number: int, title: str) -> str:
    return f"Bloc {NUM_FR.get(number, number)}. {to_speech(title)}"


# --------------------------------------------------------------------------- #
# Synthèse et montage audio
# --------------------------------------------------------------------------- #

class Speaker:
    """Enveloppe Piper : texte → tableau int16 mono, modèle chargé une seule fois."""

    def __init__(self, voice: str, length_scale: float):
        from piper import PiperVoice, SynthesisConfig

        model = VOICES_DIR / f"{voice}.onnx"
        if not model.exists():
            raise SystemExit(
                f"Modèle de voix absent : {model}\n"
                f"Lancez d'abord : python3 {Path(__file__).name} --download-voices"
            )
        self.voice = PiperVoice.load(str(model))
        self.rate = self.voice.config.sample_rate
        self.config = SynthesisConfig(length_scale=length_scale, normalize_audio=True)

    def say(self, text: str) -> np.ndarray:
        parts = [
            chunk.audio_int16_array
            for chunk in self.voice.synthesize(text, syn_config=self.config)
        ]
        if not parts:
            return np.zeros(0, dtype=np.int16)
        return np.concatenate(parts)

    def silence(self, seconds: float) -> np.ndarray:
        return np.zeros(int(self.rate * seconds), dtype=np.int16)


def build_pitch(sp: Speaker, bloc: Bloc) -> np.ndarray:
    """Titre, puis les paragraphes du pitch séparés d'une respiration."""
    pieces = [sp.silence(0.4), sp.say(title_to_speech(bloc.number, bloc.title)), sp.silence(0.9)]
    for i, para in enumerate(bloc.pitch):
        if i:
            pieces.append(sp.silence(0.55))
        pieces.append(sp.say(to_speech(para)))
    pieces.append(sp.silence(1.0))
    return np.concatenate(pieces)


def build_objection(sp: Speaker, bloc: Bloc, pause: float) -> np.ndarray:
    """Objection → silence réel pour répondre à voix haute → réponse modèle."""
    pieces = [sp.silence(0.4), sp.say(title_to_speech(bloc.number, bloc.title)), sp.silence(0.9)]

    for i, para in enumerate(bloc.objection):
        if i:
            pieces.append(sp.silence(0.5))
        pieces.append(sp.say(to_speech(para)))

    pieces += [sp.silence(0.8), sp.say(CUE_ANSWER), sp.silence(pause)]
    pieces += [sp.say(CUE_MODEL), sp.silence(0.6)]

    for i, para in enumerate(bloc.answer):
        if i:
            pieces.append(sp.silence(0.5))
        pieces.append(sp.say(to_speech(para)))

    pieces.append(sp.silence(1.0))
    return np.concatenate(pieces)


def write_mp3(audio: np.ndarray, rate: int, dest: Path, *, title: str,
              album: str, track: int | None = None) -> None:
    """Encode un tableau int16 mono en MP3 taggé, via ffmpeg (entrée WAV brute)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "s16le", "-ar", str(rate), "-ac", "1", "-i", "pipe:0",
        "-codec:a", "libmp3lame", "-b:a", "80k",
        "-metadata", f"title={title}",
        "-metadata", f"album={album}",
        "-metadata", "artist=Orbis",
    ]
    if track is not None:
        cmd += ["-metadata", f"track={track}"]
    cmd.append(str(dest))
    subprocess.run(cmd, input=audio.tobytes(), check=True)


def duration(audio: np.ndarray, rate: int) -> str:
    total = len(audio) / rate
    return f"{int(total // 60)}:{int(total % 60):02d}"


# --------------------------------------------------------------------------- #
# Téléchargement des voix
# --------------------------------------------------------------------------- #

def download_voices(names: list[str]) -> None:
    import io
    import tarfile
    import urllib.request

    VOICES_DIR.mkdir(exist_ok=True)
    for name in names:
        if (VOICES_DIR / f"{name}.onnx").exists():
            print(f"  {name} : déjà présent")
            continue
        archive, _ = AVAILABLE_VOICES[name]
        url = f"{VOICE_RELEASE}/{archive}.tar.gz"
        print(f"  {name} : téléchargement…", flush=True)
        with urllib.request.urlopen(url) as resp:
            data = resp.read()
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            tar.extractall(VOICES_DIR)
        print(f"  {name} : OK")


# --------------------------------------------------------------------------- #

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--voice", default=DEFAULT_VOICE, choices=sorted(AVAILABLE_VOICES),
                    help="voix Piper à utiliser")
    ap.add_argument("--pause", type=float, default=10.0,
                    help="durée du silence de réponse, en secondes (défaut : 10)")
    ap.add_argument("--speed", type=float, default=1.0,
                    help="facteur de durée : >1 ralentit, <1 accélère (défaut : 1.0)")
    ap.add_argument("--blocs", type=int, nargs="+", metavar="N",
                    help="ne générer que ces blocs (défaut : les 8)")
    ap.add_argument("--out", type=Path, default=OUT_DIR, help="dossier de sortie")
    ap.add_argument("--no-playlists", action="store_true",
                    help="ne pas générer les deux playlists concaténées")
    ap.add_argument("--download-voices", action="store_true",
                    help="télécharger les modèles de voix puis quitter")
    ap.add_argument("--samples", action="store_true",
                    help="générer un échantillon comparatif des voix disponibles")
    args = ap.parse_args()

    if args.download_voices:
        print("Téléchargement des voix Piper françaises :")
        download_voices(sorted(AVAILABLE_VOICES))
        return

    blocs = parse_source(SOURCE)
    if args.blocs:
        wanted = set(args.blocs)
        blocs = [b for b in blocs if b.number in wanted]
        if not blocs:
            raise SystemExit("Aucun bloc ne correspond à --blocs.")

    if args.samples:
        make_samples(blocs[0], args)
        return

    print(f"Voix : {args.voice} ({AVAILABLE_VOICES[args.voice][1]})")
    print(f"Silence de réponse : {args.pause:.0f} s\n")
    sp = Speaker(args.voice, args.speed)

    pitches: list[np.ndarray] = []
    objections: list[np.ndarray] = []

    for bloc in blocs:
        for kind in ("pitch", "objection"):
            if kind == "pitch":
                audio = build_pitch(sp, bloc)
                pitches.append(audio)
            else:
                audio = build_objection(sp, bloc, args.pause)
                objections.append(audio)

            dest = args.out / f"bloc{bloc.number}_{kind}.mp3"
            write_mp3(audio, sp.rate, dest,
                      title=f"Bloc {bloc.number} — {bloc.title} — {kind.upper()}",
                      album=f"Orbis — {kind.upper()}",
                      track=bloc.number)
            print(f"  {dest.name:26s} {duration(audio, sp.rate):>6s}")

    if not args.no_playlists and len(blocs) > 1:
        gap = sp.silence(2.0)
        for name, parts, album in (
            ("playlist_pitch.mp3", pitches, "Orbis — PITCH (playlist)"),
            ("playlist_objection.mp3", objections, "Orbis — OBJECTION (playlist)"),
        ):
            joined = np.concatenate(
                [x for part in parts for x in (part, gap)][:-1]
            )
            dest = args.out / name
            write_mp3(joined, sp.rate, dest, title=album, album=album)
            print(f"  {dest.name:26s} {duration(joined, sp.rate):>6s}")

    print(f"\nTerminé — fichiers dans {args.out}/")


def make_samples(bloc: Bloc, args) -> None:
    """Un même extrait dit par chaque voix, pour choisir."""
    out = args.out / "samples"
    extrait = to_speech(bloc.pitch[0]) + " " + to_speech(bloc.pitch[1])
    for name in sorted(AVAILABLE_VOICES):
        if not (VOICES_DIR / f"{name}.onnx").exists():
            print(f"  {name} : modèle absent, ignoré")
            continue
        sp = Speaker(name, args.speed)
        audio = sp.say(extrait)
        dest = out / f"sample_{name}.mp3"
        write_mp3(audio, sp.rate, dest, title=f"Échantillon {name}",
                  album="Orbis — échantillons de voix")
        print(f"  {dest.name:30s} {duration(audio, sp.rate):>6s}  "
              f"({AVAILABLE_VOICES[name][1]})")


if __name__ == "__main__":
    main()
