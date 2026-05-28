#!/bin/bash
# MacAPK — Build script: combines SwiftUI app + Python backend into distributable .app
set -e

PROJECT_DIR="/Users/ferdy/projects/MacAPK"
SWIFT_APP="$PROJECT_DIR/MacAPKApp/build/Build/Products/Release/MacAPKApp.app"
PYTHON_APP="$PROJECT_DIR/dist/MacAPK.app"
OUTPUT_DIR="$PROJECT_DIR/dist/native"
OUTPUT_APP="$OUTPUT_DIR/MacAPK.app"

echo "🔨 MacAPK Native Build"
echo "======================"

# Step 1: Build SwiftUI app if not present
if [ ! -d "$SWIFT_APP" ]; then
    echo "📦 Building SwiftUI app..."
    cd "$PROJECT_DIR/MacAPKApp"
    xcodebuild -project MacAPKApp.xcodeproj -scheme MacAPKApp -configuration Release -derivedDataPath build clean build 2>&1 | grep -E "(BUILD|error:)"
fi

# Step 2: Build Python backend if not present
if [ ! -d "$PYTHON_APP" ]; then
    echo "🐍 Building Python backend..."
    cd "$PROJECT_DIR"
    export PATH="$PATH:/Users/ferdy/Library/Python/3.9/bin"
    pyinstaller --clean --noconfirm MacAPK.spec 2>&1 | tail -5
fi

# Step 3: Create combined app bundle
echo "🏗️ Creating combined app bundle..."
rm -rf "$OUTPUT_APP"
mkdir -p "$OUTPUT_APP/Contents/"{MacOS,Resources,Frameworks}

# Copy SwiftUI app structure
cp -R "$SWIFT_APP/Contents/"* "$OUTPUT_APP/Contents/"

# Copy Python backend resources into the app bundle
echo "🐍 Adding Python backend..."
mkdir -p "$OUTPUT_APP/Contents/Resources/backend"
cp -R "$PYTHON_APP/Contents/Resources/"* "$OUTPUT_APP/Contents/Resources/backend/" 2>/dev/null || true
# Copy the Python executable
cp "$PYTHON_APP/Contents/MacOS/MacAPK" "$OUTPUT_APP/Contents/Resources/backend/macapk_server"

# Copy UI files
echo "🎨 Adding dashboard UI..."
mkdir -p "$OUTPUT_APP/Contents/Resources/ui"
cp "$PROJECT_DIR/ui/"* "$OUTPUT_APP/Contents/Resources/ui/"

# Copy Python source as fallback
mkdir -p "$OUTPUT_APP/Contents/Resources/backend/src/macapk"
cp -R "$PROJECT_DIR/src/macapk/"* "$OUTPUT_APP/Contents/Resources/backend/src/macapk/"
cp "$PROJECT_DIR/macapk" "$OUTPUT_APP/Contents/Resources/backend/macapk"

# Copy icon
if [ -f "$PROJECT_DIR/assets/icon.icns" ]; then
    cp "$PROJECT_DIR/assets/icon.icns" "$OUTPUT_APP/Contents/Resources/AppIcon.icns"
fi

# Update Info.plist with Python server configuration
echo "📋 Updating Info.plist..."
/usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$OUTPUT_APP/Contents/Info.plist" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$OUTPUT_APP/Contents/Info.plist"

# Codesign (ad-hoc)
echo "🔐 Code signing (ad-hoc)..."
codesign --force --deep --sign - "$OUTPUT_APP" 2>/dev/null || echo "⚠️ Code signing skipped (may need manual sign)"

echo ""
echo "✅ Build complete!"
du -sh "$OUTPUT_APP"
echo ""
echo "📍 Location: $OUTPUT_APP"
echo "🚀 To run: open \"$OUTPUT_APP\""