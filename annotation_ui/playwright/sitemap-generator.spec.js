const { test, expect } = require('@playwright/test');
const fs = require('fs');

// --- Configuration ---
const BASE_URL = 'http://localhost:3721'; // React app URL
const API_BASE_URL = 'http://localhost:8000'; // Backend API URL
const SCREENSHOTS_DIR = './sitemap_screenshots';

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

// Helper function to take a screenshot with error handling
const takeScreenshot = async (page, route, filename) => {
  try {
    console.log(`📸 Capturing: ${route}`);
    
    // Set a larger viewport to capture more content
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    await page.goto(BASE_URL + route, { waitUntil: 'networkidle', timeout: 10000 });
    
    // Wait for any dynamic content to load
    await page.waitForTimeout(1000);
    
    // Check if we're on an error page
    const pageTitle = await page.title();
    const hasErrorMessage = await page.locator('.error-message, .error-container').count() > 0;
    
    if (hasErrorMessage) {
      console.log(`❌ Error detected on ${route} - page title: ${pageTitle}`);
      const errorText = await page.locator('.error-message, .error-container').first().textContent();
      console.log(`❌ Error message: ${errorText}`);
    }
    
    // Take screenshot with better options
    await page.screenshot({ 
      path: `${SCREENSHOTS_DIR}/${filename}`, 
      fullPage: true,
      timeout: 10000
    });
    
    console.log(`✅ Screenshot saved: ${filename}`);
    return true;
  } catch (error) {
    console.log(`❌ Failed to capture ${route}: ${error.message}`);
    return false;
  }
};

// Main test suite for sitemap generation
test.describe('Enhanced Visual Sitemap Generator', () => {
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
    const publicRoutes = [
      { path: '/login', filename: '01_LoginPage.png' }
    ];
    
    for (const route of publicRoutes) {
      await takeScreenshot(page, route.path, route.filename);
    }
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
      await takeScreenshot(page, '/dashboard', '02_AnnotatorDashboard.png');
    });

    test('Capture Annotator Project Page', async () => {
      await takeScreenshot(page, `/projects/${realData.projectId}`, '03_AnnotatorProjectPage.png');
    });

    test('Capture Annotator Chat Room Page', async () => {
      await takeScreenshot(page, `/projects/${realData.projectId}/chat-rooms/${realData.chatRoomId}`, '04_AnnotatorChatRoomPage.png');
    });

    test('Capture My Annotations Page', async () => {
      await takeScreenshot(page, `/projects/${realData.projectId}/my-annotations`, '05_MyAnnotationsPage.png');
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
      await takeScreenshot(page, '/admin', '06_AdminDashboard.png');
    });

    test('Capture Admin Project Page', async () => {
      await takeScreenshot(page, `/admin/projects/${realData.projectId}`, '07_AdminProjectPage.png');
    });

    test('Capture Admin Chat Room View', async () => {
      await takeScreenshot(page, `/admin/projects/${realData.projectId}/chat-rooms/${realData.chatRoomId}`, '08_AdminChatRoomView.png');
    });

    test('Capture Annotation Analysis Page', async () => {
      await takeScreenshot(page, `/admin/projects/${realData.projectId}/analysis/${realData.chatRoomId}`, '09_AnnotationAnalysisPage.png');
    });
  });
}); 
