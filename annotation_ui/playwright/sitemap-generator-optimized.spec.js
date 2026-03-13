const { test, expect } = require('@playwright/test');
const fs = require('fs');

// --- Configuration ---
const BASE_URL = 'http://localhost:3721'; // React app URL
const API_BASE_URL = 'http://localhost:8000'; // Backend API URL
const SCREENSHOTS_DIR = './sitemap_screenshots_optimized';

// --- User Credentials ---
const ADMIN_USER = {
  username: 'admin',
  password: 'admin'
};
const ANNOTATOR_USER = {
  username: 'anotaozuil',
  password: 'ChangeMe123!'
};

// Helper function to log in a user and return the page
const login = async (page, user) => {
  await page.goto(`${BASE_URL}/login`);
  await page.locator('input#username').fill(user.username);
  await page.locator('input[type="password"]').fill(user.password);
  await page.locator('button[type="submit"]').click();
  // Wait for navigation to complete after login
  await page.waitForURL(url => url.pathname !== '/login');
};

// Helper function to get auth token from localStorage
const getAuthToken = async (page) => {
  return await page.evaluate(() => localStorage.getItem('access_token'));
};

// Helper function to fetch real data from the API
const fetchRealData = async (page, userCredentials) => {
  console.log('🔍 Fetching real data from API...');
  
  // Login to get access token
  await login(page, userCredentials);
  const token = await getAuthToken(page);
  
  if (!token) {
    throw new Error('Failed to get authentication token');
  }
  
  // Use the specific project ID that we know has good data
  const TARGET_PROJECT_ID = 21; // "Excel Import Project" - confirmed to have good data
  
  console.log(`🎯 Using target project ID: ${TARGET_PROJECT_ID}`);
  
  // Fetch the specific project data
  const projectResponse = await page.request.get(`${API_BASE_URL}/admin/projects`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (!projectResponse.ok()) {
    throw new Error(`Failed to fetch projects: ${projectResponse.status()}`);
  }
  
  const projectsData = await projectResponse.json();
  const targetProject = projectsData.find(p => p.id === TARGET_PROJECT_ID);
  
  if (!targetProject) {
    throw new Error(`Target project with ID ${TARGET_PROJECT_ID} not found`);
  }
  
  console.log('🎯 Using project:', targetProject.name, 'ID:', targetProject.id);
  
  // Fetch chat rooms for the target project
  const chatRoomsResponse = await page.request.get(`${API_BASE_URL}/projects/${TARGET_PROJECT_ID}/chat-rooms`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (!chatRoomsResponse.ok()) {
    throw new Error(`Failed to fetch chat rooms: ${chatRoomsResponse.status()}`);
  }
  
  const chatRoomsData = await chatRoomsResponse.json();
  console.log(`💬 Found ${chatRoomsData.length} chat rooms in project ${targetProject.name}`);
  
  if (!chatRoomsData || chatRoomsData.length === 0) {
    throw new Error(`No chat rooms found for project ${TARGET_PROJECT_ID}`);
  }
  
  const firstChatRoom = chatRoomsData[0];
  console.log('🎯 Using chat room:', firstChatRoom.name, 'ID:', firstChatRoom.id);
  
  return {
    projectId: targetProject.id,
    projectName: targetProject.name,
    chatRoomId: firstChatRoom.id,
    chatRoomName: firstChatRoom.name
  };
};

// Helper function to take optimized screenshots for documentation
const takeOptimizedScreenshot = async (page, route, filename, options = {}) => {
  try {
    console.log(`📸 Capturing optimized: ${route}`);
    
    // Set viewport size for consistent screenshots
    await page.setViewportSize({ width: 1400, height: 900 });
    
    await page.goto(BASE_URL + route, { waitUntil: 'networkidle', timeout: 10000 });
    
    // Wait for dynamic content and animations
    await page.waitForTimeout(1500);
    
    // Check if we're on an error page
    const pageTitle = await page.title();
    const hasErrorMessage = await page.locator('.error-message, .error-container').count() > 0;
    
    if (hasErrorMessage) {
      console.log(`❌ Error detected on ${route} - page title: ${pageTitle}`);
      const errorText = await page.locator('.error-message, .error-container').first().textContent();
      console.log(`❌ Error message: ${errorText}`);
    }
    
    // Take screenshot with optimized settings
    const screenshotOptions = {
      path: `${SCREENSHOTS_DIR}/${filename}`,
      timeout: 10000,
      type: 'png',
      quality: 90,
      ...options
    };
    
    // For specific routes, use different capture strategies
    if (route.includes('chat-rooms')) {
      // For chat room pages, capture the main content area
      screenshotOptions.fullPage = false;
      screenshotOptions.clip = { x: 0, y: 0, width: 1400, height: 900 };
    } else {
      // For other pages, capture full page but with reasonable limits
      screenshotOptions.fullPage = true;
    }
    
    await page.screenshot(screenshotOptions);
    
    console.log(`✅ Optimized screenshot saved: ${filename}`);
    return true;
  } catch (error) {
    console.log(`❌ Failed to capture ${route}: ${error.message}`);
    return false;
  }
};

// Main test suite for optimized sitemap generation
test.describe('Optimized Visual Sitemap Generator', () => {
  let realData;

  // Create the screenshot directory and fetch real data
  test.beforeAll(async ({ browser }) => {
    // Create screenshots directory
    if (!fs.existsSync(SCREENSHOTS_DIR)) {
      fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
    }
    
    // Fetch real data from API
    const page = await browser.newPage();
    try {
      realData = await fetchRealData(page, ADMIN_USER);
      console.log('✅ Real data fetched successfully:', realData);
    } catch (error) {
      console.error('❌ Failed to fetch real data:', error.message);
      throw error;
    } finally {
      await page.close();
    }
  });

  // --- Public Routes ---
  test('Capture Public Routes', async ({ page }) => {
    await takeOptimizedScreenshot(page, '/login', '01_LoginPage.png');
  });

  // --- Annotator Routes ---
  test.describe('Capture Annotator Routes', () => {
    let page;

    test.beforeAll(async ({ browser }) => {
      page = await browser.newPage();
      await login(page, ANNOTATOR_USER);
    });
    
    test.afterAll(async () => {
      await page.close();
    });

    test('Capture Annotator Dashboard', async () => {
      await takeOptimizedScreenshot(page, '/dashboard', '02_AnnotatorDashboard.png');
    });

    test('Capture Annotator Project Page', async () => {
      await takeOptimizedScreenshot(page, `/projects/${realData.projectId}`, '03_AnnotatorProjectPage.png');
    });

    test('Capture Annotator Chat Room Page', async () => {
      await takeOptimizedScreenshot(page, `/projects/${realData.projectId}/chat-rooms/${realData.chatRoomId}`, '04_AnnotatorChatRoomPage.png');
    });

    test('Capture My Annotations Page', async () => {
      await takeOptimizedScreenshot(page, `/projects/${realData.projectId}/my-annotations`, '05_MyAnnotationsPage.png');
    });
  });
  
  // --- Admin Routes ---
  test.describe('Capture Admin Routes', () => {
    let page;

    test.beforeAll(async ({ browser }) => {
      page = await browser.newPage();
      await login(page, ADMIN_USER);
    });

    test.afterAll(async () => {
      await page.close();
    });

    test('Capture Admin Dashboard', async () => {
      await takeOptimizedScreenshot(page, '/admin', '06_AdminDashboard.png');
    });

    test('Capture Admin Project Page', async () => {
      await takeOptimizedScreenshot(page, `/admin/projects/${realData.projectId}`, '07_AdminProjectPage.png');
    });

    test('Capture Admin Chat Room View', async () => {
      await takeOptimizedScreenshot(page, `/admin/projects/${realData.projectId}/chat-rooms/${realData.chatRoomId}`, '08_AdminChatRoomView.png');
    });

    test('Capture Annotation Analysis Page', async () => {
      await takeOptimizedScreenshot(page, `/admin/projects/${realData.projectId}/analysis/${realData.chatRoomId}`, '09_AnnotationAnalysisPage.png');
    });
  });
}); 
