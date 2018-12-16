from jnius import autoclass
Locale = autoclass('java.util.Locale')

print("PYJNIUS LOADED")

PythonActivity = autoclass('org.kivy.android.PythonActivity')

Context = autoclass('android.content.Context')
Intent = autoclass('android.content.Intent')
Activity = PythonActivity.mActivity

TextToSpeech = autoclass('android.speech.tts.TextToSpeech')

tts = TextToSpeech(PythonActivity.mActivity, None)
tts.setLanguage(Locale.US)


def vibrate(n):
    try:
        vibrator = Activity.getSystemService(Context.VIBRATOR_SERVICE)
        vibrator.vibrate(n)
    except Exception as e:
        print(e)


def speak(delta, text=''):
    tts.speak(text, TextToSpeech.QUEUE_FLUSH, None)

