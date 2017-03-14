import datetime, threading


def time_delta(**kwargs):
  """Return datetime object based on a delta with the current time"""
  return datetime.datetime.now() + datetime.timedelta(**kwargs)

def repeater(interval, endtime, message):
  """
    Create a decorator to repeat a function:
    usage:
      as a decorator
      @repeater(interval = 1, endtime = time_delta(seconds = 12) )
      def foo():

      function call
      repeater(interval = 1, endtime = time_delta(seconds = 12) )(foo)(*args, **kwargs)
  """
  def repeater_decorator(fn):
      def run(*k, **kw):
          # call function if end time is not reached yet
          if not endtime or time_delta() < endtime:
            if message: print(time_delta(), message)
            fn(*k, **kw)
          # Recursive timed call to run if endtime wont be reached after next interval
          if not endtime or time_delta() + datetime.timedelta(seconds = interval) < endtime:
            t = threading.Timer(interval = interval, function=run, args=k, kwargs = kw)
            t.start()
      return run
  return repeater_decorator