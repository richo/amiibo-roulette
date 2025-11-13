mkdir -p amiibos
find "./db/Amiibo Bin/Animal Crossing Amiibo/Amiibo Cards/" -name '*.bin' | while read path; do
  name=$(echo $path | grep -o "[A-Za-z]*\.bin" | sed -e 's/bin/eml/')
  ./mfubin2eml "$path" > amiibos/$name
done
