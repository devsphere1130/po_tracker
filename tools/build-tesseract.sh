# Builds a self-contained Linux Tesseract (eng + tha) into backend/vendor/tesseract for Vercel.
# Ubuntu 20.04 (glibc 2.31) binaries run on Vercel's Amazon Linux 2023 (glibc 2.34).
# Run from the project root (PowerShell):
#   docker run --rm -v "${PWD}:/work" ubuntu:20.04 bash -c "tr -d '\r' < /work/tools/build-tesseract.sh | bash"
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng tesseract-ocr-tha
OUT=/work/backend/vendor/tesseract
rm -rf "$OUT" && mkdir -p "$OUT/bin" "$OUT/lib" "$OUT/tessdata"
cp /usr/bin/tesseract "$OUT/bin/"
# Copy shared libraries, except the glibc core that the host already provides.
ldd /usr/bin/tesseract | awk '/=>/ {print $3}' \
  | grep -vE '/(libc|libm|libpthread|libdl|librt)\.so|ld-linux' \
  | xargs -I{} cp -L {} "$OUT/lib/"
TD=/usr/share/tesseract-ocr/4.00/tessdata
cp "$TD/eng.traineddata" "$TD/tha.traineddata" "$TD/osd.traineddata" "$OUT/tessdata/"
chmod +x "$OUT/bin/tesseract"
echo "--- self-test ---"
LD_LIBRARY_PATH="$OUT/lib" TESSDATA_PREFIX="$OUT/tessdata" "$OUT/bin/tesseract" --version | head -1
LD_LIBRARY_PATH="$OUT/lib" TESSDATA_PREFIX="$OUT/tessdata" "$OUT/bin/tesseract" --list-langs
du -sh "$OUT"
