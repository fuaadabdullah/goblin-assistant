const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

// Function to compress a single image
async function compressImage(inputPath, outputPath, quality = 80) {
  try {
    await sharp(inputPath)
      .png({ quality, effort: 6 })
      .jpeg({ quality, effort: 6 })
      .webp({ quality: Math.floor(quality * 0.8) })
      .toFile(outputPath);
    
    const originalSize = fs.statSync(inputPath).size;
    const compressedSize = fs.statSync(outputPath).size;
    const savings = ((originalSize - compressedSize) / originalSize * 100).toFixed(1);
    
    console.log(`✅ Compressed ${path.basename(inputPath)}: ${originalSize} → ${compressedSize} bytes (${savings}% savings)`);
    
    // Replace original with compressed version
    fs.renameSync(outputPath, inputPath);
  } catch (error) {
    console.error(`❌ Error compressing ${inputPath}:`, error.message);
  }
}

async function compressImages() {
  const directories = ['screenshots', 'dist'];
  
  for (const dir of directories) {
    if (!fs.existsSync(dir)) continue;
    
    console.log(`\n📁 Processing ${dir}/ directory...`);
    const files = fs.readdirSync(dir);
    
    for (const file of files) {
      const inputPath = path.join(dir, file);
      const stat = fs.statSync(inputPath);
      
      // Skip directories and very small files
      if (stat.isDirectory() || stat.size < 1024) continue;
      
      // Only process image files
      const ext = path.extname(file).toLowerCase();
      if (['.png', '.jpg', '.jpeg', '.webp'].includes(ext)) {
        const tempPath = inputPath + '.temp'; // Temporary file
        await compressImage(inputPath, tempPath);
      }
    }
  }
  
  console.log('\n🎉 Image compression complete!');
}

compressImages();
