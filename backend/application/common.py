import datetime

def epoch_to_datetime(epoch_time):
  """Converts epoch time to a datetime object."""
  return datetime.datetime.fromtimestamp(epoch_time)
