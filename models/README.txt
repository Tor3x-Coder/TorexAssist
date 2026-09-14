# Put your unzipped Vosk model folder in here.
#
# The default expectation is:
#     models/vosk-model-small-en-us-0.15
#
# But ANY Vosk English model works. For example the bigger, much
# better-hearing one:
#     models/vosk-model-en-us-0.22
#
# Download from https://alphacephei.com/vosk/models
#   - vosk-model-small-en-us-0.15  (about 40 MB, light and quick)
#   - vosk-model-en-us-0.22        (about 1.8 GB, best accuracy)
#
# Whatever folder name you end up with, point config.ini at it:
#     [LISTENING]
#     model_folder = models/vosk-model-en-us-0.22
#
# The model files are ignored by git on purpose - they are big
# files that belong to somebody else, no reason to upload them.
