// Paste this in your browser console to test the API directly
// Bypasses the chat UI to directly make API calls and log responses

(function() {
  const API_URL = 'https://chatwithwebsite-lyart.vercel.app/api/chat';
  const currentUrl = window.location.href;
  
  console.log(`Testing API with current website: ${currentUrl}`);
  
  // Direct API test function
  async function testApi(message = "What is this website about?") {
    console.log(`Sending test request for message: "${message}"`);
    
    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: currentUrl,
          message: message,
          debug: true // Always enable debug for testing
        })
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('------------------------------');
      console.log('🟢 API Response:');
      console.log(`Answer: "${data.response}"`);
      console.log(`Website ID: ${data.website_id}`);
      
      if (data.debug_info) {
        console.log('------------------------------');
        console.log('🔍 Debug Information:');
        console.log(data.debug_info);
      }
      
      return data;
    } catch (error) {
      console.error('❌ Error testing API:', error);
    }
  }
  
  // Expose the function to the global scope for further testing
  window.testRag = testApi;
  
  // Run the test immediately with default message
  testApi().then(() => {
    console.log('------------------------------');
    console.log('✅ Test complete. You can run more tests with:');
    console.log('testRag("your question here")');
  });
})(); 