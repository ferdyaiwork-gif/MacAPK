#!/bin/bash
# MacAPK — Build final DMG with native SwiftUI app + Python backend
set -e

PROJECT_DIR="/Users/ferdy/projects/MacAPK"
BUILD_DIR="$PROJECT_DIR/dist"
NATIVE_APP="$PROJECT_DIR/MacAPKApp/build/Build/Products/Release/MacAPKApp.app"
DMG_NAME="MacAPK-1.0.0"
VOLUME_NAME="MacAPK"

echo "🔨 MacAPK DMG Builder"
echo "====================="

# Step 1: Build SwiftUI app if needed
if [ ! -d "$NATIVE_APP" ]; then
    echo "📦 Building SwiftUI app..."
    cd "$PROJECT_DIR/MacAPKApp"
    xcodebuild -project MacAPKApp.xcodeproj -scheme MacAPKApp -configuration Release -derivedDataPath build clean build 2>&1 | tail -3
    echo "✅ SwiftUI app built"
fi

# Step 2: Build Python backend if needed
if [ ! -d "$PROJECT_DIR/dist/MacAPK.app" ]; then
    echo "🐍 Building Python backend..."
    cd "$PROJECT_DIR"
    export PATH="$PATH:/Users/ferdy/Library/Python/3.9/bin"
    pyinstaller --clean --noconfirm MacAPK.spec 2>&1 | tail -3
    echo "✅ Python backend built"
fi

# Step 3: Create combined app bundle
echo "🏗️ Creating combined MacAPK.app..."
rm -rf "$BUILD_DIR/native/MacAPK.app"
mkdir -p "$BUILD_DIR/native/MacAPK.app/Contents/"{MacOS,Resources,Frameworks}

# Copy SwiftUI app structure
cp -R "$NATIVE_APP/Contents/"* "$BUILD_DIR/native/MacAPK.app/Contents/"

# Copy Python backend
mkdir -p "$BUILD_DIR/native/MacAPK.app/Contents/Resources/backend"
cp -R "$PROJECT_DIR/dist/MacAPK.app/Contents/Resources/"* "$BUILD_DIR/native/MacAPK.app/Contents/Resources/backend/" 2>/dev/null || true
cp "$PROJECT_DIR/dist/MacAPK.app/Contents/MacOS/MacAPK" "$BUILD_DIR/native/MacAPK.app/Contents/Resources/backend/macapk_server"

# Copy UI files
mkdir -p "$BUILD_DIR/native/MacAPK.app/Contents/Resources/ui"
cp "$PROJECT_DIR/ui/"* "$BUILD_DIR/native/MacAPK.app/Contents/Resources/ui/"

# Copy Python source as fallback
mkdir -p "$BUILD_DIR/native/MacAPK.app/Contents/Resources/backend/src/macapk"
cp -R "$PROJECT_DIR/src/macapk/"* "$BUILD_DIR/native/MacAPK.app/Contents/Resources/backend/src/macapk/"
cp "$PROJECT_DIR/macapk" "$BUILD_DIR/native/MacAPK.app/Contents/Resources/backend/macapk"

# Copy icon
if [ -f "$PROJECT_DIR/assets/icon.icns" ]; then
    cp "$PROJECT_DIR/assets/icon.icns" "$BUILD_DIR/native/MacAPK.app/Contents/Resources/AppIcon.icns"
fi

# Update Info.plist
/usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$BUILD_DIR/native/MacAPK.app/Contents/Info.plist" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$BUILD_DIR/native/MacAPK.app/Contents/Info.plist"

# Codesign
echo "🔐 Code signing..."
codesign --force --deep --sign - "$BUILD_DIR/native/MacAPK.app" 2>/dev/null || echo "⚠️ Code signing skipped"

echo "✅ App bundle: $(du -sh "$BUILD_DIR/native/MacAPK.app" | cut -f1)"

# Step 4: Build DMG
echo "📦 Building DMG..."
rm -f "$BUILD_DIR/$DMG_NAME.dmg"
DMG_TEMP="$BUILD_DIR/dmg_temp"
rm -rf "$DMG_TEMP"
mkdir -p "$DMG_TEMP"

# Copy app to DMG temp
cp -R "$BUILD_DIR/native/MacAPK.app" "$DMG_TEMP/"

# Create Applications symlink
ln -s /Applications "$DMG_TEMP/Applications"

# Create DMG using hdiutil
hdiutil create -volname "$VOLUME_NAME" -srcfolder "$DMG_TEMP" -ov -format UDZO "$BUILD_DIR/$DMG_NAME.dmg"

# Cleanup
rm -rf "$DMG_TEMP"

echo ""
echo "✅ DMG build done!"
echo "📍 DMG: $BUILD_DIR/$DMG_NAME.dmg"
du -sh "$BUILD_DIR/$DMG_NAME.dmg"
echo ""
echo "🚀 To install: open \"$BUILD_DIR/$DMG_NAME.dmg\""