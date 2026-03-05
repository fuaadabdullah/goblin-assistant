import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function getMetrics() {
  const srcPath = path.join(__dirname, '../src');
  const testPath = path.join(__dirname, '../tests');

  const metrics = {
    files: {
      total: 0,
      components: 0,
      utils: 0,
      test: 0,
    },
    lines: {
      total: 0,
      average: 0,
      max: 0,
      maxFile: '',
    },
    tests: {
      total: 0,
      coverage: 0,
    },
    issues: {
      eslint: 0,
      complexity: 0,
      naming: 0,
    },
    timestamp: new Date().toISOString(),
  };

  // Collect file metrics
  function analyzeDirectory(dirPath, type = 'src') {
    if (!fs.existsSync(dirPath)) return;

    const files = fs.readdirSync(dirPath, { recursive: true });

    files.forEach((file) => {
      const filePath = path.join(dirPath, file);
      if (!fs.statSync(filePath).isFile()) return;

      const ext = path.extname(file);
      if (!['.js', '.jsx', '.ts', '.tsx'].includes(ext)) return;

      metrics.files.total++;

      // Categorize files
      if (type === 'test') {
        metrics.files.test++;
      } else {
        const content = fs.readFileSync(filePath, 'utf8');
        const lines = content.split('\n').length;
        metrics.lines.total += lines;

        if (lines > metrics.lines.max) {
          metrics.lines.max = lines;
          metrics.lines.maxFile = path.relative(process.cwd(), filePath);
        }

        // Check if it's a component (React-like patterns)
        if (
          content.includes('export default') &&
          (content.includes('function') || content.includes('const') || content.includes('class'))
        ) {
          if (
            file.includes('Component') ||
            file.includes('Page') ||
            content.includes('React.') ||
            content.includes('jsx') ||
            (content.includes('<') && content.includes('>'))
          ) {
            metrics.files.components++;
          } else {
            metrics.files.utils++;
          }
        } else {
          metrics.files.utils++;
        }

        // Check for naming issues
        if (file.includes(' ') || file.includes('_')) {
          metrics.issues.naming++;
        }

        // Simple complexity check (nested functions/loops)
        const complexityIndicators = (content.match(/function|if|for|while|switch/g) || []).length;
        if (complexityIndicators > 10) {
          metrics.issues.complexity++;
        }
      }
    });
  }

  // Analyze source and test directories
  analyzeDirectory(srcPath, 'src');
  analyzeDirectory(testPath, 'test');

  // Calculate averages
  if (metrics.files.total > 0) {
    metrics.lines.average = Math.round(metrics.lines.total / metrics.files.total);
  }

  // Get ESLint violations
  try {
    const eslintOutput = execSync('npm run lint 2>&1 || true', { encoding: 'utf8' });
    // Count error/warning lines (rough estimate)
    const errorLines = eslintOutput
      .split('\n')
      .filter((line) => line.includes('error') || line.includes('warning')).length;
    metrics.issues.eslint = errorLines;
  } catch (error) {
    console.warn("⚠️  Could not run ESLint. Make sure it's configured.");
    metrics.issues.eslint = -1; // Indicate ESLint not available
  }

  // Get test coverage if available
  try {
    const coveragePath = path.join(__dirname, '../coverage/coverage-summary.json');
    if (fs.existsSync(coveragePath)) {
      const coverage = JSON.parse(fs.readFileSync(coveragePath, 'utf8'));
      metrics.tests.coverage = Math.round(coverage.total.lines.pct);
    }
  } catch (error) {
    console.warn('⚠️  Could not read test coverage. Run tests with coverage first.');
  }

  // Count test files
  metrics.tests.total = metrics.files.test;

  return metrics;
}

function generateReport(metrics) {
  console.log('\n📈 Code Quality Metrics Report');
  console.log('='.repeat(50));
  console.log(`Generated: ${new Date(metrics.timestamp).toLocaleString()}\n`);

  console.log('📁 File Statistics:');
  console.log(`  Total files: ${metrics.files.total}`);
  console.log(`  Components: ${metrics.files.components}`);
  console.log(`  Utilities: ${metrics.files.utils}`);
  console.log(`  Test files: ${metrics.files.test}\n`);

  console.log('📝 Code Metrics:');
  console.log(`  Total lines: ${metrics.lines.total.toLocaleString()}`);
  console.log(`  Average lines/file: ${metrics.lines.average}`);
  console.log(`  Largest file: ${metrics.lines.maxFile} (${metrics.lines.max} lines)\n`);

  console.log('🧪 Testing:');
  console.log(`  Test files: ${metrics.tests.total}`);
  console.log(
    `  Coverage: ${metrics.tests.coverage > 0 ? metrics.tests.coverage + '%' : 'Not available'}\n`
  );

  console.log('⚠️  Code Quality Issues:');
  console.log(
    `  ESLint violations: ${metrics.issues.eslint >= 0 ? metrics.issues.eslint : 'ESLint not configured'}`
  );
  console.log(`  High complexity files: ${metrics.issues.complexity}`);
  console.log(`  Poor naming: ${metrics.issues.naming}\n`);

  // Quality score
  const qualityScore = calculateQualityScore(metrics);
  console.log('🎯 Quality Score:', qualityScore.score);
  console.log(`   Grade: ${qualityScore.grade}`);
  console.log(`   ${qualityScore.feedback}\n`);

  // Recommendations
  generateRecommendations(metrics);
}

function calculateQualityScore(metrics) {
  let score = 100;

  // Deduct for issues
  score -= metrics.issues.eslint * 2;
  score -= metrics.issues.complexity * 5;
  score -= metrics.issues.naming * 3;

  // Deduct for low coverage
  if (metrics.tests.coverage > 0 && metrics.tests.coverage < 80) {
    score -= 80 - metrics.tests.coverage;
  }

  // Deduct for large files
  if (metrics.lines.max > 500) {
    score -= 10;
  }

  score = Math.max(0, Math.min(100, score));

  let grade, feedback;
  if (score >= 90) {
    grade = 'A';
    feedback = 'Excellent code quality! Keep up the great work.';
  } else if (score >= 80) {
    grade = 'B';
    feedback = 'Good quality. Minor improvements needed.';
  } else if (score >= 70) {
    grade = 'C';
    feedback = 'Average quality. Consider refactoring.';
  } else if (score >= 60) {
    grade = 'D';
    feedback = 'Below average. Significant improvements needed.';
  } else {
    grade = 'F';
    feedback = 'Poor quality. Immediate attention required.';
  }

  return { score: Math.round(score), grade, feedback };
}

function generateRecommendations(metrics) {
  console.log('💡 Recommendations:');

  if (metrics.issues.eslint > 0) {
    console.log('  • Fix ESLint violations to improve code consistency');
  }

  if (metrics.issues.complexity > 0) {
    console.log('  • Refactor high-complexity files (consider breaking them down)');
  }

  if (metrics.issues.naming > 0) {
    console.log('  • Use consistent naming conventions (camelCase/kebab-case)');
  }

  if (metrics.tests.coverage < 80 && metrics.tests.coverage > 0) {
    console.log('  • Increase test coverage to at least 80%');
  }

  if (metrics.lines.max > 300) {
    console.log('  • Break down large files into smaller, focused modules');
  }

  if (metrics.files.components === 0 && metrics.files.total > 0) {
    console.log('  • Consider organizing code into reusable components');
  }

  console.log('');
}

// Run the report
if (import.meta.url === `file://${process.argv[1]}`) {
  try {
    const metrics = getMetrics();
    generateReport(metrics);
  } catch (error) {
    console.error('❌ Error generating metrics report:', error.message);
    process.exit(1);
  }
}

export { getMetrics, generateReport, calculateQualityScore };
