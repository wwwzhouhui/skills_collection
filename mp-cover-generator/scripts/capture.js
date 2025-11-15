#!/usr/bin/env node

/**
 * 公众号封面 HTML 转图片工具
 * 使用 Playwright 截取 HTML 文件的高质量截图
 *
 * 使用方法:
 *   node capture.js <html-file-path> <output-image-path> [options]
 *
 * 参数:
 *   html-file-path: 输入的 HTML 文件路径
 *   output-image-path: 输出的图片路径 (支持 .png 和 .jpg)
 *
 * 选项:
 *   --width: 视口宽度 (默认: 2560，适配公众号封面)
 *   --height: 视口高度 (默认: 1097，21:9 比例)
 *   --quality: JPEG 质量 (默认: 95，仅 JPEG 格式有效)
 *   --wait: 等待时间(毫秒)，确保图片完全加载 (默认: 2000)
 *   --scale: 设备像素比，用于高清截图 (默认: 2)
 *
 * 示例:
 *   node capture.js cover.html cover.png
 *   node capture.js cover.html cover.jpg --quality 95
 *   node capture.js cover.html cover.png --width 2560 --height 1097 --scale 2
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// 解析命令行参数
function parseArgs() {
    const args = process.argv.slice(2);

    if (args.length < 2) {
        console.error('❌ 错误: 需要提供 HTML 文件路径和输出图片路径');
        console.error('使用方法: node capture.js <html-file-path> <output-image-path> [options]');
        console.error('');
        console.error('示例:');
        console.error('  node capture.js cover.html cover.png');
        console.error('  node capture.js cover.html cover.jpg --quality 95');
        process.exit(1);
    }

    const config = {
        htmlPath: args[0],
        outputPath: args[1],
        width: 2560,
        height: 1097,  // 21:9 比例 (2560/21*9 ≈ 1097)
        quality: 95,
        wait: 2000,
        scale: 2  // 2倍像素密度，生成高清图片
    };

    // 解析选项
    for (let i = 2; i < args.length; i++) {
        if (args[i] === '--width' && i + 1 < args.length) {
            config.width = parseInt(args[i + 1]);
            i++;
        } else if (args[i] === '--height' && i + 1 < args.length) {
            config.height = parseInt(args[i + 1]);
            i++;
        } else if (args[i] === '--quality' && i + 1 < args.length) {
            config.quality = parseInt(args[i + 1]);
            i++;
        } else if (args[i] === '--wait' && i + 1 < args.length) {
            config.wait = parseInt(args[i + 1]);
            i++;
        } else if (args[i] === '--scale' && i + 1 < args.length) {
            config.scale = parseFloat(args[i + 1]);
            i++;
        }
    }

    return config;
}

// 验证文件
function validateFiles(config) {
    // 检查输入文件是否存在
    if (!fs.existsSync(config.htmlPath)) {
        console.error(`❌ 错误: HTML 文件不存在: ${config.htmlPath}`);
        process.exit(1);
    }

    // 确保输出目录存在
    const outputDir = path.dirname(config.outputPath);
    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }

    // 检查输出格式
    const ext = path.extname(config.outputPath).toLowerCase();
    if (ext !== '.png' && ext !== '.jpg' && ext !== '.jpeg') {
        console.error('❌ 错误: 输出格式必须是 .png 或 .jpg');
        process.exit(1);
    }

    config.format = ext === '.png' ? 'png' : 'jpeg';
}

// 主函数
async function captureScreenshot() {
    const config = parseArgs();
    validateFiles(config);

    console.log('📸 公众号封面截图配置:');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log(`  📄 HTML 文件: ${config.htmlPath}`);
    console.log(`  🖼️  输出路径: ${config.outputPath}`);
    console.log(`  📐 视口大小: ${config.width}x${config.height}`);
    console.log(`  🎯 像素密度: ${config.scale}x`);
    console.log(`  📊 输出格式: ${config.format.toUpperCase()}`);
    if (config.format === 'jpeg') {
        console.log(`  💎 JPEG 质量: ${config.quality}%`);
    }
    console.log(`  ⏱️  等待时间: ${config.wait}ms`);
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('');

    let browser;
    try {
        // 启动浏览器
        console.log('🚀 启动浏览器...');
        browser = await chromium.launch({
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
        });

        // 创建页面（高 DPI 支持）
        const context = await browser.newContext({
            viewport: {
                width: config.width,
                height: config.height
            },
            deviceScaleFactor: config.scale,
            acceptDownloads: true,
            ignoreHTTPSErrors: true
        });
        const page = await context.newPage();

        // 设置页面默认行为，避免弹窗
        page.on('dialog', async dialog => {
            await dialog.accept();
        });

        // 转换为绝对路径
        const absoluteHtmlPath = path.resolve(config.htmlPath);
        const fileUrl = `file://${absoluteHtmlPath}`;

        console.log(`📖 加载页面: ${fileUrl}`);
        await page.goto(fileUrl, {
            waitUntil: 'networkidle',
            timeout: 30000
        });

        // 等待页面完全渲染
        console.log(`⏳ 等待 ${config.wait}ms 确保页面完全渲染...`);
        await page.waitForTimeout(config.wait);

        // 等待所有图片加载完成
        console.log('🖼️  等待所有图片加载完成...');
        await page.evaluate(() => {
            return Promise.all(
                Array.from(document.images)
                    .filter(img => !img.complete)
                    .map(img => new Promise(resolve => {
                        img.onload = img.onerror = resolve;
                    }))
            );
        });

        // 等待所有字体加载完成
        await page.evaluate(() => {
            return document.fonts.ready;
        });

        // 获取页面实际高度
        const contentHeight = await page.evaluate(() => {
            return Math.max(
                document.documentElement.scrollHeight,
                document.documentElement.offsetHeight,
                document.documentElement.clientHeight,
                document.body.scrollHeight,
                document.body.offsetHeight,
                document.body.clientHeight
            );
        });

        console.log(`📏 检测到页面实际高度: ${contentHeight}px`);

        // 调整视口高度以适应完整内容
        if (contentHeight > config.height) {
            console.log(`⚠️  页面高度 (${contentHeight}px) 超过视口高度 (${config.height}px)`);
            console.log(`🔧 自动调整视口高度为 ${contentHeight}px`);
            await page.setViewportSize({
                width: config.width,
                height: contentHeight
            });
        }

        console.log('📸 正在截取完整页面...');

        // 截图选项
        const screenshotOptions = {
            path: config.outputPath,
            fullPage: true,  // 截取完整页面
            type: config.format
        };

        // 如果是 JPEG，添加质量参数
        if (config.format === 'jpeg') {
            screenshotOptions.quality = config.quality;
        }

        await page.screenshot(screenshotOptions);

        // 获取实际视口尺寸
        const actualViewport = page.viewportSize();

        console.log('');
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log('✅ 截图成功！');
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log(`  📁 保存位置: ${config.outputPath}`);

        // 获取文件大小
        const stats = fs.statSync(config.outputPath);
        const fileSizeKB = (stats.size / 1024).toFixed(2);
        const fileSizeMB = (stats.size / (1024 * 1024)).toFixed(2);

        if (stats.size < 1024 * 1024) {
            console.log(`  📦 文件大小: ${fileSizeKB} KB`);
        } else {
            console.log(`  📦 文件大小: ${fileSizeMB} MB`);
        }

        // 计算实际输出分辨率（使用实际视口尺寸）
        const actualWidth = actualViewport.width * config.scale;
        const actualHeight = actualViewport.height * config.scale;
        console.log(`  🎨 实际分辨率: ${actualWidth}x${actualHeight} 像素`);
        console.log(`  📐 视口尺寸: ${actualViewport.width}x${actualViewport.height} 像素`);

        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log('');

        await browser.close();
        process.exit(0);

    } catch (error) {
        console.error('');
        console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.error('❌ 截图失败！');
        console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.error(`错误信息: ${error.message}`);
        console.error('');

        if (error.message.includes('net::ERR_FILE_NOT_FOUND')) {
            console.error('💡 提示: 请检查 HTML 文件路径是否正确');
        } else if (error.message.includes('timeout')) {
            console.error('💡 提示: 页面加载超时，可以尝试增加 --wait 参数');
        } else if (error.message.includes('Failed to launch')) {
            console.error('💡 提示: 请确保 Playwright 浏览器已正确安装');
            console.error('   运行: npm install 或 npx playwright install chromium');
        }

        console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.error('');

        if (browser) {
            await browser.close();
        }
        process.exit(1);
    }
}

// 运行
captureScreenshot();
