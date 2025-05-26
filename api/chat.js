export default async function handler(req, res) {
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
  res.status(200).json({ answer: data.choices?.[0]?.message?.content || "Nepodařilo se načíst odpověď." });
}
