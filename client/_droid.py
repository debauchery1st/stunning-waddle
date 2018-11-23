from jnius import autoclass
print("PYJNIUS LOADED")
# test for an intent passed to us
PythonActivity = autoclass('org.kivy.android.PythonActivity')
activity = PythonActivity.mActivity
intent = activity.getIntent()
intent_data = intent.getData()
if intent_data:
    file_uri = intent_data.toString()


def vibrate():
    try:
        intent = autoclass('android.content.Intent')
        Context = autoclass('android.content.Context')
        vibrator = activity.getSystemService(Context.VIBRATOR_SERVICE)
        vibrator.vibrate(234)
    except Exception as e:
        print(e)
