# Orbis — audios d'ancrage oral

Les fichiers audio générés à partir des scripts Orbis, plus le script qui les fabrique.
Deux versions du corpus, à partir de deux documents source :

| Document source | Dossier audio | Format |
|---|---|---|
| `Orbis_Scripts_Audio.md` | `audio/` | version courte — pitchs de ~1 min |
| `Orbis_Scripts_Audio_3min.md` | `audio_3min/` | version longue — pitchs de ~2 min, objections développées |

## Ce qu'il y a dans chaque dossier

| Fichier | Contenu |
|---|---|
| `bloc1_pitch.mp3` … `bloc8_pitch.mp3` | Le script PITCH du bloc, précédé de son titre |
| `bloc1_objection.mp3` … `bloc8_objection.mp3` | L'objection → **un silence réel pour répondre à voix haute** → la réponse modèle |
| `playlist_pitch.mp3` | Les 8 pitchs à la suite |
| `playlist_objection.mp3` | Les 8 exercices d'objection à la suite |
| `samples/` | Le même extrait dit par chaque voix disponible, pour comparer |

Durées des playlists :

| | PITCH | OBJECTION |
|---|---|---|
| `audio/` (version courte) | 7:41 | 8:34 |
| `audio_3min/` (version longue) | 17:19 | 13:45 |

Tout est en MP3 mono 80 kbit/s : ça se dépose tel quel dans une app de podcast, sur un
téléphone ou dans une playlist voiture.

## Comment s'en servir

- **Playlist PITCH** — en boucle, en voiture ou en marchant, jusqu'à ce que ça coule tout seul.
- **Playlist OBJECTION** — l'objection est énoncée, puis vient la relance *« À vous.
  Répondez à voix haute. »* suivie d'un vrai silence : vous répondez pour de bon, à voix
  haute, avant d'entendre la réponse modèle. C'est l'entraînement actif, celui qui crée
  la conviction sous pression.

Le silence de réponse est de **10 s** dans `audio/` (le document disait « cinq secondes »,
trop court pour formuler une réponse complète sans mettre en pause) et de **15 s** dans
`audio_3min/`, dont les objections sont plus riches et le document dit « prenez le temps ».
Réglable avec `--pause`.

### Sur la durée des pitchs

Le document long s'appelle « 3 minutes », mais les pitchs sortent entre 1:50 et 2:21. Ce
n'est pas un texte tronqué — c'est le même texte, intégralement — simplement dit plus vite
qu'un orateur humain ne le ferait. Pour se rapprocher d'un débit de scène :

```bash
python3 generate_audio.py --source Orbis_Scripts_Audio_3min.md --pause 15 --speed 1.15
```

À 1.15, le bloc 1 passe de 2:21 à 2:33.

## Regénérer les fichiers

```bash
pip install piper-tts                       # synthèse vocale neuronale, hors ligne
sudo apt-get install -y ffmpeg              # encodage MP3
python3 generate_audio.py --download-voices # ~150 Mo de modèles, une seule fois

python3 generate_audio.py                                                  # version courte
python3 generate_audio.py --source Orbis_Scripts_Audio_3min.md --pause 15  # version longue
```

Le dossier de sortie se déduit du nom du document (`…_3min.md` → `audio_3min/`), sauf si
vous passez `--out`.

Options utiles :

```bash
--voice fr-gilles-low   # voix masculine
--pause 20              # silence de réponse plus long
--speed 1.15            # débit plus lent
--blocs 3 7             # regénérer seulement certains blocs
--samples               # comparer les voix
```

Le script relit le markdown à chaque exécution : si vous retouchez un script, relancez la
commande et les MP3 correspondants sont refaits.

## Choix techniques

**Pourquoi pas `say` (option A des documents) ?** C'est une commande macOS ; ce dépôt a été
construit sous Linux.

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
  `RPA`, `RH`, `IA`, `IT`) pour éviter qu'ils soient lus comme des mots ;
- remplace la consigne écrite *« [Répondez à voix haute…] »* par une relance dite à voix
  haute suivie d'un silence réel ;
- pose des respirations calibrées entre les paragraphes, avant et après le silence de
  réponse.

## Fichiers

```
Orbis_Scripts_Audio.md        document source, version courte
Orbis_Scripts_Audio_3min.md   document source, version longue
generate_audio.py             le générateur
audio/                        les MP3 de la version courte
audio_3min/                   les MP3 de la version longue
voices/                       les modèles Piper (non versionnés — cf. --download-voices)
```
