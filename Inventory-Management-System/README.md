<div align="center">

&#x20; <h1>🏪 Standalone Offline Inventory \& Store Billing System</h1>

&#x20; <p><b>A clean, high-performance offline desktop point of sale application, database manager, and automated PDF invoice engine.</b></p>

</div>



<hr>



<h3>📋 Project Overview \& Features</h3>

<p>This desktop software provides an efficient, completely localized infrastructure to streamline product lifecycle tracking, stock control parameters, and customer invoicing workflows. Engineered for maximum reliability, it functions 100% offline with zero external cloud or network dependencies.</p><br>

<img src="screenshots\\preview1.png" alt="Company Logo" width="180" onerror="this.src='https://placehold.co/180x180?text=preview'">

<img src="screenshots\\\\preview2.png" alt="Company Logo" width="180" onerror="this.src='https://placehold.co/180x180?text=preview'">

<br>

<ul>

&#x20; <li><b>📦 Pure Offline Local Database:</b> Fully powered by a fast, embedded SQLite relational system (<code>inventory\_store\_database.db</code>) ensuring instant data access and absolute local security.</li>

&#x20; <li><b>🧾 Automated Financial Calculators:</b> Pre-configured mathematical engines computing backward/forward Indian GST breakdowns along with gross-profit margins.</li>

&#x20; <li><b>📄 Dynamic ReportLab PDF Billing:</b> Generates high-fidelity, grid-aligned, print-ready A4 invoices directly into a dedicated local directory.</li>

&#x20; <li><b>📊 Analytics \& Data Exports:</b> Built-in background logging capable of converting relational data tables into standard Excel spreadsheets using Pandas.</li>

&#x20; <li><b>🏷️ Collision-Free Barcoding:</b> Multi-threaded numeric algorithms designed to generate unique, secure inventory barcodes for store items.</li>

</ul>



<hr>



<h3>⚙️ Mandatory Developer Configuration</h3>

<p>Before launching the application runtime, you must map your personal business identity and graphical assets into the engine. Open the script and update the branding layout strings shown below:</p>



<pre>

<code>

\# 🔍 LOCATE AND REPLACE THESE LINES INSIDE THE INVOICE GENERATION LOGIC:



LOGO\_FILENAME = "assets/company\_logo.png"   # Replace with your logo file

COMPANY\_INFO = {

&#x20;   "name": "ADD COMPANY LOGO",

&#x20;   "address\_line1": "ADD ADDRESS",

&#x20;   "address\_line2": "ADD ADDRESS-2",

&#x20;   "phone": "Phone: PHONE NUMBER"

}

</code>

</pre>



<p><i>Note: Ensure your business graphical logo asset is dropped securely into the local <code>assets/</code> directory matching the string configuration pointer path perfectly.</i></p>



<hr>



<h3>🚀 Installation \& Setup</h3>

<p>Follow these quick steps to set up your environment libraries and launch the system:</p>



<h4>1. Install the Required Libraries</h4>

<p>This application relies on external data processing and document generation libraries. Open your terminal or command prompt inside this folder and execute the installation string:</p>



<pre><code>pip install -r requirements.txt</code></pre>



<p>If you prefer to install the specific dependencies manually, use this syntax:</p>

<pre><code>pip install pandas reportlab xlsxwriter Pillow</code></pre>



<h4>2. Run the Application</h4>

<p>Launch the main environment file using Python. The local relational files will safely initialize automatically on your machine during the first boot:</p>

<pre><code>python Inventory\_Store\_Manager.py</code></pre>



<hr>



<h3>💾 Direct Download Link</h3>

<p>If you want to download just this individual project folder without cloning the entire repository, click the link below to get an instant ZIP file:</p>



<p>👉 <b><a href="https://downgit.github.io/#/home?url=https://github.com/yourusername/My-Developer-Portfolio/tree/main/Inventory-Management-System" target="\_blank">Click Here to Instantly Download this Project Folder (.ZIP)</a></b></p>



<hr>



<h3>📂 Folder Structure</h3>

<pre>

├── Inventory\_Store\_Manager.py      # Core Desktop Python Application Framework

├── requirements.txt               # Documented Module \& Package Dependency Blueprint

├── inventory\_store\_database.db    # Dynamic SQLite Relational Store Engine (Auto-Generated)

├── assets/

│   └── company\_logo.png           # Destination Vector for Your Branding Assets

└── invoices\_pdf/                  # Destination for Printed Invoice Documents

</pre>

