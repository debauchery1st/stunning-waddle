from jnius import autoclass
print("PYJNIUS LOADED")

PythonActivity = autoclass('org.kivy.android.PythonActivity')

Context = autoclass('android.content.Context')
Intent = autoclass('android.content.Intent')
Activity = PythonActivity.mActivity


def vibrate(n):
    try:
        vibrator = Activity.getSystemService(Context.VIBRATOR_SERVICE)
        vibrator.vibrate(n)
    except Exception as e:
        print(e)
