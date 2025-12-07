// Build script for Brave-compatible extension
const fs = require("fs-extra");
const path = require("path");

async function buildForBrave() {
    const distDir = path.join(__dirname, "dist", "brave");

    try {
        // Create dist directory
        await fs.ensureDir(distDir);

        // Copy files for Brave build
        const filesToCopy = [
            { src: "manifest.json", dest: "manifest.json" },
            { src: "SnifferEx_brave.js", dest: "SnifferEx.js" },
            { src: "index.html", dest: "index.html" },
            { src: "background.js", dest: "background.js" },
            { src: "content.js", dest: "content.js" },
            { src: "style.css", dest: "style.css" },
        ];

        const foldersToCopy = ["libs"];

        for (const file of filesToCopy) {
            const srcPath = path.join(__dirname, file.src);
            const destPath = path.join(distDir, file.dest);

            if (await fs.pathExists(srcPath)) {
                await fs.copy(srcPath, destPath);
                console.log(`✓ Copied ${file.src} → ${file.dest}`);
            } else {
                console.log(`⚠ File not found: ${file.src}`);
            }
        }

        for (const folder of foldersToCopy) {
            const srcFolderPath = path.join(__dirname, folder);
            const destFolderPath = path.join(distDir, folder);
            if (await fs.pathExists(srcFolderPath)) {
                await fs.copy(srcFolderPath, destFolderPath);
                console.log(`✓ Copied ${folder} directory`);
            }
        }

        // Copy icons directory
        const iconsDir = path.join(__dirname, "icons");
        if (await fs.pathExists(iconsDir)) {
            await fs.copy(iconsDir, path.join(distDir, "icons"));
            console.log("✓ Copied icons directory");
        }

        console.log("\n🎉 Brave extension build completed!");
        console.log(`📂 Output directory: ${distDir}`);
        console.log("\nTo install:");
        console.log("1. Open brave://extensions/");
        console.log("2. Enable Developer mode");
        console.log('3. Click "Load unpacked"');
        console.log(`4. Select the folder: ${distDir}`);
    } catch (error) {
        console.error("❌ Build failed:", error);
        process.exit(1);
    }
}

buildForBrave();
