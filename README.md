# Orbis — audios d'ancrage oral

Les 16 fichiers audio générés à partir de `Orbis_Scripts_Audio.md`, plus le script
qui les fabrique.

## Ce qu'il y a dans `audio/`

| Fichier | Contenu |
|---|---|
| `bloc1_pitch.mp3` … `bloc8_pitch.mp3` | Le script PITCH du bloc, précédé de son titre |
| `bloc1_objection.mp3` … `bloc8_objection.mp3` | L'objection → **10 s de silence pour répondre à voix haute** → la réponse modèle |
| `playlist_pitch.mp3` | Les 8 pitchs à la suite (7 min 41) |
| `playlist_objection.mp3` | Les 8 exercices d'objection à la suite (8 min 34) |
| `samples/` | Le même extrait dit par chaque voix disponible, pour comparer |

Tout est en MP3 mono 80 kbit/s : ça se dépose tel quel dans une app de podcast,
sur un téléphone ou dans une playlist voiture.

## Comment s'en servir

- **Playlist PITCH** — en boucle, en voiture ou en marchant, jusqu'à ce que ça coule tout seul.
- **Playlist OBJECTION** — l'objection est énoncée, puis vient la relance *« À vous.
  Répondez à voix haute. »* suivie d'un vrai silence de 10 secondes : vous répondez
  pour de bon, à voix haute, avant d'entendre la réponse modèle. C'est l'entraînement
  actif, celui qui crée la conviction sous pression.

Le document d'origine suggérait 5 secondes ; 10 laissent le temps de formuler une
réponse complète sans mettre le lecteur en pause. Ajustable (voir `--pause`).

## Regénérer les fichiers

```bash
pip install piper-tts                       # synthèse vocale neuronale, hors ligne
sudo apt-get install -y ffmpeg              # encodage MP3
python3 generate_audio.py --download-voices # ~150 Mo de modèles, une seule fois
python3 generate_audio.py
```

Options utiles :

```bash
python3 generate_audio.py --voice fr-gilles-low  # voix masculine
python3 generate_audio.py --pause 15             # silence de réponse plus long
python3 generate_audio.py --speed 1.1            # débit plus lent
python3 generate_audio.py --blocs 3 7            # regénérer seulement 2 blocs
python3 generate_audio.py --samples              # comparer les voix
```

Le script relit `Orbis_Scripts_Audio.md` à chaque exécution : si vous retouchez un
script, relancez la commande et les MP3 correspondants sont refaits.

## Choix techniques

**Pourquoi pas `say` (option A du document) ?** C'est une commande macOS ; ce dépôt a
été construit sous Linux.

**Pourquoi pas ElevenLabs (option B) ?** Aucune clé `ELEVENLABS_API_KEY` disponible, et
l'accès réseau sortant vers les services de synthèse en ligne est fermé ici.

**D'où vient la voix, alors ?** De [Piper](https://github.com/rhasspy/piper), un modèle
neuronal VITS qui tourne entièrement en local. Voix françaises disponibles :

| Voix | Timbre | Qualité |
|---|---|---|
| `fr-siwis-medium` *(défaut)* | féminine | 22 kHz, medium |
| `fr-gilles-low` | masculine | 16 kHz, low |
| `fr-siwis-low` | féminine | 16 kHz, low |

C'est une voix de synthèse locale : nette et parfaitement intelligible, mais en dessous
d'ElevenLabs sur la chaleur et l'intonation. Si vous voulez le rendu le plus naturel
possible pour un usage en boucle, fournissez une clé ElevenLabs et le script pourra être
branché dessus — la structure (découpage, silences, montage) reste identique.

**Adaptations du texte pour l'oral** — le script `generate_audio.py` :

- retire le balisage markdown, les guillemets et les crochets ;
- transforme les tirets cadratins en respirations ;
- épelle les sigles (`P&L` → « P et L », `COO` → « C O O », `DRH`, `CFO`, `ESN`, `SLA`,
  `RPA`, `IA`, `IT`) pour éviter qu'ils soient lus comme des mots ;
- remplace la consigne écrite *« [Répondez à voix haute. Prenez cinq secondes.] »* par
  une relance dite à voix haute suivie d'un silence réel ;
- pose des respirations calibrées entre les paragraphes, avant et après le silence de
  réponse.

## Fichiers

```
Orbis_Scripts_Audio.md   le document source (les 8 blocs)
generate_audio.py        le générateur
audio/                   les MP3
voices/                  les modèles Piper (non versionnés — cf. --download-voices)
```
