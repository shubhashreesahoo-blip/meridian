import streamlit as st
import anthropic
import base64
from PIL import Image
import io
import json

st.set_page_config(page_title="Meridian", layout="wide")

# Custom CSS
st.markdown("""
<style>
.main { background-color: #F9F7F4; }
h1 { color: #5A4A40; font-family: 'Outfit', sans-serif; }
.stButton>button { background-color: #B8956A; color: white; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

st.title("🏗️ Meridian")
st.subheader("See It. Price It. Win It.")
st.write("Upload a construction photo and get instant cost estimates.")

# Input API key
api_key = st.text_input("Anthropic API Key (get free from console.anthropic.com):", type="password")

# Upload photo
uploaded_file = st.file_uploader("Upload construction photo (JPG or PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        image = Image.open(uploaded_file)
        st.image(image, caption="Your photo", use_column_width=True)
    
    with col2:
        st.write("**File Details:**")
        st.write(f"- Name: {uploaded_file.name}")
        st.write(f"- Size: {uploaded_file.size / 1024 / 1024:.2f} MB")

if uploaded_file and api_key and st.button("Generate Estimate", key="generate"):
    with st.spinner("Analyzing photo... (30-90 seconds)"):
        try:
            # Convert image to base64
            image = Image.open(uploaded_file)
            img_bytes = io.BytesIO()
            image.thumbnail((1920, 1080), Image.LANCZOS)
            image.save(img_bytes, format='JPEG', quality=82)
            b64 = base64.b64encode(img_bytes.getvalue()).decode()
            
            # Call Anthropic API
            client = anthropic.Anthropic(api_key=api_key)
            
            prompt = """You are a senior construction estimator with 25+ years experience. Analyze this construction photo and produce a detailed cost estimate.

Identify every visible construction element and estimate quantities using scale references (vehicles, people, standard dimensions).
Use current 2024-2025 California construction pricing.
Provide THREE price points: conservative, realistic, optimistic.
Flag low-confidence items so the estimator knows where to verify.

Return ONLY valid JSON:
{
  "project_type": "specific project type",
  "site_description": "what's visible in the photo",
  "items": [
    {
      "code": "item code",
      "description": "specific item description",
      "quantity": number,
      "unit": "unit type (CY, SF, LF, EA, etc)",
      "unit_cost_low": number,
      "unit_cost_high": number,
      "cost_low": number,
      "cost_high": number,
      "confidence": "high/medium/low",
      "notes": "assumption made"
    }
  ],
  "summary": {
    "total_low": number,
    "total_mid": number,
    "total_high": number,
    "confidence_average": percentage,
    "key_risks": ["list of risks"],
    "contingency_recommended": percentage
  },
  "disclaimers": "ROM estimate only. Site visit required."
}"""
            
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=2500,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            )
            
            # Parse response
            raw = response.content[0].text.strip()
            if raw.startswith('```'):
                start = raw.find('{')
                end = raw.rfind('}') + 1
                raw = raw[start:end]
            
            result = json.loads(raw)
            
            # Display results
            st.success("✓ Estimate Generated!")
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Conservative", f"${result['summary']['total_low']/1000:.1f}K")
            with col2:
                st.metric("Realistic", f"${result['summary']['total_mid']/1000:.1f}K")
            with col3:
                st.metric("Optimistic", f"${result['summary']['total_high']/1000:.1f}K")
            with col4:
                st.metric("Confidence", f"{result['summary']['confidence_average']}%")
            
            # Project details
            st.subheader(result['project_type'])
            st.write(result['site_description'])
            
            # Line items table
            st.subheader("Line Items")
            
            table_data = []
            for item in result['items']:
                table_data.append({
                    "Code": item['code'],
                    "Description": item['description'],
                    "Qty": f"{item['quantity']:.0f}",
                    "Unit": item['unit'],
                    "Unit Price": f"${item['unit_cost_low']:.0f}-${item['unit_cost_high']:.0f}",
                    "Total": f"${item['cost_high']/1000:.1f}K",
                    "Confidence": item['confidence']
                })
            
            st.dataframe(table_data, use_container_width=True)
            
            # Risks
            if result['summary']['key_risks']:
                st.subheader("⚠️ Cost Risks to Verify")
                for risk in result['summary']['key_risks']:
                    st.write(f"- {risk}")
            
            # Download JSON
            st.download_button(
                label="Download Full Estimate (JSON)",
                data=json.dumps(result, indent=2),
                file_name="estimate.json",
                mime="application/json"
            )
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.write("**Troubleshooting:**")
            st.write("1. Verify API key is correct")
            st.write("2. Check you have API credits at console.anthropic.com")
            st.write("3. Try a simpler/clearer photo")
            st.write("4. Wait 60 seconds and try again")

# Footer
st.markdown("---")
st.markdown("Meridian © 2024 · Built for Construction Estimators")
