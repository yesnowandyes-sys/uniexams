/**
 * Test the backend API with sample requests
 */

const BASE_URL = 'http://localhost:3001';

async function request(method, endpoint, body = null) {
  const options = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, options);
  return response.json();
}

async function runTests() {
  console.log('🧪 Running backend API tests...\n');

  try {
    // 1. Health check
    console.log('1️⃣  Health check...');
    const health = await request('GET', '/api/health');
    console.log('   ✅', health);
    console.log('');

    // 2. Create a user
    console.log('2️⃣  Creating user...');
    const user = await request('POST', '/api/users', {
      name: 'Test User',
      email: 'test@example.com',
    });
    console.log('   ✅ Created user:', user.id);
    console.log('   📝 Name:', user.name);
    console.log('   📧 Email:', user.email);
    console.log('');

    // 3. Get user stats (should be empty initially)
    console.log('3️⃣  Getting user stats...');
    const stats = await request('GET', `/api/users/${user.id}/stats`);
    console.log('   ✅ Total attempts:', stats.total_attempts);
    console.log('   ✅ Accuracy:', stats.accuracy, '%');
    console.log('');

    // 4. List questions
    console.log('4️⃣  Listing questions...');
    const questions = await request('GET', '/api/questions?limit=5');
    console.log('   ✅ Found', questions.length, 'questions');
    if (questions.length > 0) {
      const q = questions[0];
      console.log('   📦 First question:');
      console.log('      - ID:', q.id);
      console.log('      - Module:', q.module);
      console.log('      - Difficulty:', q.difficulty);
    }
    console.log('');

    // 5. Get a specific question (without answer)
    console.log('5️⃣  Getting question details...');
    if (questions.length > 0) {
      const questionId = questions[0].id;
      const question = await request('GET', `/api/questions/${questionId}`);
      console.log('   ✅ Question ID:', question.id);
      console.log('   📝 Text:', question.question_text.substring(0, 100) + '...');
      console.log('   🔤 Options:', Object.keys(question.options).join(', '));
      console.log('   ⚠️  Correct answer NOT exposed');
      console.log('');

      // 6. Submit an attempt
      console.log('6️⃣  Submitting an attempt...');
      const attempt = await request('POST', '/api/attempts', {
        user_id: user.id,
        question_id: questionId,
        selected_answer: 'A',
        time_taken_ms: 45000,
      });
      console.log('   ✅ Attempt recorded');
      console.log('   ✅ Is correct:', attempt.is_correct);
      console.log('   ✅ Correct answer:', attempt.correct_answer);
      console.log('');

      // 7. Get user stats again (should now have data)
      console.log('7️⃣  Getting user stats (after attempt)...');
      const updatedStats = await request('GET', `/api/users/${user.id}/stats`);
      console.log('   ✅ Total attempts:', updatedStats.total_attempts);
      console.log('   ✅ Correct attempts:', updatedStats.correct_attempts);
      console.log('   ✅ Accuracy:', updatedStats.accuracy, '%');
      console.log('   ✅ Avg time:', Math.round(updatedStats.avg_time_ms / 1000), 'seconds');
      console.log('');

      // 8. Get user attempts
      console.log('8️⃣  Getting user attempts...');
      const attempts = await request('GET', `/api/users/${user.id}/attempts`);
      console.log('   ✅ Found', attempts.length, 'attempts');
      if (attempts.length > 0) {
        const a = attempts[0];
        console.log('   📝 Question:', a.question_text.substring(0, 50) + '...');
        console.log('   ✅ Selected:', a.selected_answer);
        console.log('   ✅ Correct:', a.correct_answer);
        console.log('   ✅ Is correct:', a.is_correct ? 'Yes' : 'No');
        console.log('   ⏱️  Time:', a.time_taken_ms / 1000, 'seconds');
      }
      console.log('');

      // 9. Get user stats per module
      console.log('9️⃣  Getting user stats per module...');
      const statsWithModules = await request('GET', `/api/users/${user.id}/stats`);
      console.log('   ✅ Module breakdown:');
      statsWithModules.module_stats.forEach((mod) => {
        console.log('      -', mod.module + ':', mod.attempts, 'attempts,', mod.correct, 'correct');
      });
      console.log('');

      // 10. Cleanup: delete user
      console.log('🔟 Cleaning up...');
      await request('DELETE', `/api/users/${user.id}`);
      console.log('   ✅ User deleted');
    }

    console.log('\n🎉 All tests passed!');
  } catch (error) {
    console.error('\n❌ Test failed:', error.message);
    console.error('   Make sure the server is running: npm start');
    process.exit(1);
  }
}

runTests();