import { execSync } from 'child_process';

console.log('🚀 Setting up Goblin Assistant quality tools...\n');

try {
  console.log('1. Installing dependencies...');
  execSync('npm install --legacy-peer-deps', { stdio: 'inherit' });

  console.log('\n3. Setting up Git hooks...');
  execSync('npx husky install', { stdio: 'inherit' });

  console.log('\n4. Running initial lint (may fail due to config issues)...');
  try {
    execSync('npm run lint', { stdio: 'inherit' });
  } catch (error) {
    console.log('⚠️  Lint failed - this is expected if ESLint config needs updating');
  }

  console.log('\n5. Running initial tests...');
  try {
    execSync('npm test', { stdio: 'inherit' });
  } catch (error) {
    console.log('⚠️  Tests failed - this is expected if test setup needs configuration');
  }

  console.log('\n✅ Setup complete!');
  console.log('\n📋 Next steps:');
  console.log('  - Run `npm run quality:check` to see current issues');
  console.log('  - Run `npm run quality:fix` to auto-fix what you can');
  console.log('  - Review the output and manually fix remaining issues');
} catch (error) {
  console.error('\n❌ Setup failed:', error.message);
  process.exit(1);
}
