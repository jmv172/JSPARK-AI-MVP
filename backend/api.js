
/* J-SPARK AI - Backend connection layer */

window.JSPARK_API = {
  async chat(message, language = "English", mode = "chat") {
    const baseUrl = window.JSPARK_CONFIG?.API_BASE_URL;

    if (!baseUrl || baseUrl.includes("YOUR-BACKEND-URL")) {
      throw new Error(
        "J-SPARK AI backend is not deployed yet. Your message is safe; please try again after deployment."
      );
    }

    const response = await fetch(`${baseUrl}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        messages: [
          { role: "user", content: message }
        ],
        language,
        mode
      })
    });

    if (!response.ok) {
      throw new Error(`AI service error (${response.status}).`);
    }

    const data = await response.json();
    return data.reply;
  }
};
