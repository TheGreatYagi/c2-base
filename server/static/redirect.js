// Define the sleep function
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function delayedRedirect() {
    console.log("Waiting 3 seconds...");
    await sleep(3000); // 3 seconds
    
    window.location.href = "http://localhost:8080/admin/zombies";
}

// Call the function to start the timer and redirect
delayedRedirect();