export default async function handler(req, res) {
  try {
    const { question } = await req.json();

    const response = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`
      },
      body: JSON.stringify({
        model: "gpt-4",
        messages: [{ role: "user", content: question }],
        temperature: 0.5
      })
    });

    const data = await response.json();

    // LOGUJEME ODEZVU do konzole (Vercel → Logs)
    console.log("OpenAI odpověď:", JSON.stringify(data, null, 2));

    if (data.error) {
      res.status(500).json({ answer: `Chyba z OpenAI: ${data.error.message}` });
      return;
    }

    const answer = data.choices?.[0]?.message?.content || "Žádná odpověď nebyla vrácena.";
    res.status(200).json({ answer });
  } catch (error) {
    console.error("Chyba serveru:", error);
    res.status(500).json({ answer: "Interní chyba serveru." });
  }
}
