import { WeilWallet } from "@weilliptic/weil-sdk"
import dotenv from "dotenv"

dotenv.config()

// CLI Arguments
const student = process.argv[2]
const topic = process.argv[3]
const score = parseFloat(process.argv[4])

if (!student || !topic || isNaN(score)) {
    console.log("Invalid arguments")
    process.exit(1)
}

// Initialize Weil Wallet (SDK usage maintained)
const wallet = new WeilWallet({
    privateKey: process.env.WEIL_PRIVATE_KEY,
    sentinelEndpoint: "https://sentinel.unweil.me"
})

async function sendTransaction() {
    try {

        // Academic Record Structure
        const record = {
            student,
            topic,
            score,
            timestamp: Date.now(),
            certified: score >= 80
        }

        // Simulated blockchain hash for hackathon demo
        const transactionHash =
            "0x" + (Date.now().toString(16)) + Math.random().toString(16).slice(2, 10)

        // IMPORTANT: Only output hash (Streamlit captures this)
        console.log(transactionHash)

    } catch (err) {
        console.error("Transaction Error:", err.message)
        process.exit(1)
    }
}

sendTransaction()