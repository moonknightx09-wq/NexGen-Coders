import crypto from "crypto";

const args = process.argv.slice(2);

const student = args[0];
const score = args[1];

const record = {
    student: student,
    score: score,
    timestamp: Date.now()
};

const hash = crypto
    .createHash("sha256")
    .update(JSON.stringify(record))
    .digest("hex");

console.log(hash);