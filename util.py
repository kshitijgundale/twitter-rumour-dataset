def clean_text(s):
  st = ''.join([i if ord(i) < 128 else ' ' for i in s])
  st = st.replace('"', '')
  st = st.replace('.', '')
  st = st.replace(')', '').replace('(', '')
  st = st.replace(",", '')
  return st.strip()