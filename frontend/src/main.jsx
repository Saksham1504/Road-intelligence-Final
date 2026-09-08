import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { MapContainer, TileLayer, Marker, Popup, LayersControl } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "./style.css";

const API = import.meta.env.VITE_API_BASE_URL || `http://${window.location.hostname}:8000`;

function formatComplaintDate(value) {
  if (!value) return "-";
  const normalized = /Z|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

function formatComplaintDateParts(value) {
  if (!value) return { date: "-", time: "" };
  const normalized = /Z|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`;
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return { date: "-", time: "" };
  return {
    date: new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "2-digit", year: "numeric" }).format(parsed),
    time: new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(parsed),
  };
}

function fileToDataUrl(selectedFile) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(selectedFile);
  });
}

function dataUrlToFile(dataUrl, filename) {
  const [header, body] = dataUrl.split(",");
  const binary = atob(body);
  const bytes = Uint8Array.from(binary, character => character.charCodeAt(0));
  const mime = header.match(/data:(.*);base64/)?.[1] || "image/jpeg";
  return new File([bytes], filename, { type: mime });
}

const CITIZEN_LANGUAGES = [
  "English", "Hindi", "Bengali", "Marathi", "Telugu", "Tamil", "Gujarati", "Urdu", "Kannada", "Odia", "Malayalam", "Punjabi", "Assamese", "Maithili", "Santali", "Kashmiri", "Nepali", "Sindhi", "Konkani", "Dogri", "Manipuri (Meitei)", "Bodo", "Sanskrit", "Bhojpuri", "Rajasthani", "Chhattisgarhi", "Magahi", "Awadhi", "Haryanvi", "Marwari", "Bundeli", "Bagheli", "Garhwali", "Kumaoni", "Tulu", "Mewari", "Malvi", "Nimadi", "Gondi", "Khasi", "Mizo", "Garo", "Kokborok", "Ho", "Mundari", "Kurukh (Oraon)", "Khandeshi", "Bhili/Bhilodi", "Angika", "Kachchi", "Saurashtra", "Kodava (Kodagu)", "Tuluva", "Banjari", "Lambadi/Banjari", "Pahari", "Konyak", "Ao", "Angami", "Lepcha"
];

const ENGLISH = {
  eyebrow: "SMART ROAD MONITORING", tagline: "Report road damage. Capture location. Let AI help authorities prioritize repairs.", online: "● SYSTEM ONLINE", citizenReport: "📱 Citizen Report", governmentDashboard: "🏛️ Government Dashboard", citizenReporting: "CITIZEN REPORTING", heroTitle: "Spot a damaged road? Report it in under a minute.", heroDescription: "Take a photo from your phone, allow GPS access, and our AI model identifies potholes, cracks and manholes before the complaint reaches the maintenance dashboard.", step1: "Capture road photo", step2: "GPS attaches location", step3: "AI detects damage", step4: "Complaint reaches authority", newComplaint: "NEW COMPLAINT", reportRoadDamage: "Report Road Damage", gpsAi: "📍 GPS + AI", locationAttached: "Your location is attached to this report so the authority can find the affected road.", takePhoto: "Take Road Photo", cameraHint: "Camera opens on supported phones", gallery: "Choose from Gallery", currentLocation: "📍 Your current location", refreshGps: "Refresh GPS", locationNotCaptured: "Location not captured yet", coordinatesSent: "Coordinates are sent with the image for road verification.", submit: "🚨 DETECT DAMAGE & REGISTER COMPLAINT", analyzing: "🤖 AI ANALYZING...", complaintRegistered: "COMPLAINT REGISTERED", reportReceived: "Report received", detectedDamage: "Detected damage", noDamage: "No damage", locationAddress: "Location address", gpsCoordinates: "GPS coordinates", whatNext: "What happens next?", nextDescription: "The AI result, GPS coordinates and road address are stored as a complaint. Authorized government officers can verify the location and update the repair status.", gpsUnsupported: "GPS is not supported by this browser.", gettingGps: "Getting high-accuracy GPS location...", locationCaptured: "Location captured", permissionDenied: "Location permission denied.", permissionHelp: "Open the lock icon beside the address, allow Location, then press Refresh GPS.", gpsUnavailable: "Location is currently unavailable. Move outdoors or check device location services and try again.", photoRequired: "Please take a road photo or choose an image.", needGps: "We need your GPS location before registering the complaint.", analyzingMessage: "AI is analyzing the road image and registering your report...", noDamageFound: "No supported road damage was detected. Try a clearer road image.", complaintSubmitted: "Complaint submitted successfully", detectionFailed: "Detection failed. Check FastAPI and YOLO.", addressUnavailable: "Address unavailable", filterLanguages: "Filter languages", noLanguages: "No languages found"
};

const TRANSLATIONS = {
  English: ENGLISH,
  Hindi: { citizenReporting: "नागरिक रिपोर्टिंग", heroTitle: "सड़क खराब है? एक मिनट में रिपोर्ट करें।", heroDescription: "अपने फोन से फोटो लें, GPS की अनुमति दें और हमारा AI मॉडल गड्ढों, दरारों और मैनहोल की पहचान करेगा।", step1: "सड़क की फोटो लें", step2: "GPS स्थान जोड़ेगा", step3: "AI नुकसान पहचानेगा", step4: "शिकायत अधिकारी तक पहुंचेगी", newComplaint: "नई शिकायत", reportRoadDamage: "सड़क की खराबी रिपोर्ट करें", locationAttached: "अधिकारी सड़क खोज सकें, इसलिए आपका स्थान इस रिपोर्ट के साथ जोड़ा गया है।", takePhoto: "सड़क की फोटो लें", cameraHint: "समर्थित फोन पर कैमरा खुलेगा", gallery: "गैलरी से चुनें", currentLocation: "📍 आपका वर्तमान स्थान", refreshGps: "GPS रीफ्रेश करें", locationNotCaptured: "स्थान अभी प्राप्त नहीं हुआ", coordinatesSent: "सड़क सत्यापन के लिए निर्देशांक फोटो के साथ भेजे जाएंगे।", submit: "🚨 नुकसान पहचानें और शिकायत दर्ज करें", analyzing: "🤖 AI जांच कर रहा है...", complaintRegistered: "शिकायत दर्ज हो गई", reportReceived: "रिपोर्ट प्राप्त हुई", detectedDamage: "पहचाना गया नुकसान", noDamage: "कोई नुकसान नहीं", locationAddress: "स्थान का पता", gpsCoordinates: "GPS निर्देशांक", whatNext: "अब आगे क्या होगा?", nextDescription: "AI परिणाम, GPS निर्देशांक और सड़क का पता शिकायत के रूप में सुरक्षित हैं। अधिकृत अधिकारी स्थान की जांच कर सकते हैं और मरम्मत की स्थिति अपडेट कर सकते हैं।", gpsUnsupported: "इस ब्राउज़र में GPS उपलब्ध नहीं है।", gettingGps: "सटीक GPS स्थान प्राप्त किया जा रहा है...", locationCaptured: "स्थान प्राप्त हुआ", permissionDenied: "स्थान की अनुमति नहीं मिली। कृपया अनुमति दें और फिर प्रयास करें।", photoRequired: "कृपया सड़क की फोटो लें या कोई चित्र चुनें।", needGps: "शिकायत दर्ज करने से पहले आपका GPS स्थान आवश्यक है।", analyzingMessage: "AI सड़क की फोटो की जांच करके आपकी रिपोर्ट दर्ज कर रहा है...", noDamageFound: "सड़क का कोई समर्थित नुकसान नहीं मिला। अधिक स्पष्ट फोटो आजमाएं।", complaintSubmitted: "शिकायत सफलतापूर्वक दर्ज हुई" },
  Bengali: { citizenReporting: "নাগরিক রিপোর্টিং", heroTitle: "রাস্তা ক্ষতিগ্রস্ত? এক মিনিটে রিপোর্ট করুন।", heroDescription: "ফোন দিয়ে ছবি তুলুন, GPS অনুমতি দিন এবং আমাদের AI গর্ত, ফাটল ও ম্যানহোল শনাক্ত করবে।", step1: "রাস্তার ছবি তুলুন", step2: "GPS অবস্থান যোগ করবে", step3: "AI ক্ষতি শনাক্ত করবে", step4: "অভিযোগ কর্তৃপক্ষের কাছে যাবে", newComplaint: "নতুন অভিযোগ", reportRoadDamage: "রাস্তার ক্ষতি রিপোর্ট করুন", locationAttached: "কর্তৃপক্ষ যাতে রাস্তা খুঁজে পায়, তাই আপনার অবস্থান রিপোর্টের সঙ্গে যুক্ত করা হয়েছে।", takePhoto: "রাস্তার ছবি তুলুন", cameraHint: "সমর্থিত ফোনে ক্যামেরা খুলবে", gallery: "গ্যালারি থেকে বেছে নিন", currentLocation: "📍 আপনার বর্তমান অবস্থান", refreshGps: "GPS রিফ্রেশ করুন", locationNotCaptured: "অবস্থান এখনও পাওয়া যায়নি", coordinatesSent: "রাস্তা যাচাইয়ের জন্য স্থানাঙ্ক ছবির সঙ্গে পাঠানো হবে।", submit: "🚨 ক্ষতি শনাক্ত করে অভিযোগ নথিভুক্ত করুন", analyzing: "🤖 AI বিশ্লেষণ করছে...", complaintRegistered: "অভিযোগ নথিভুক্ত হয়েছে", reportReceived: "রিপোর্ট পাওয়া গেছে", detectedDamage: "শনাক্ত ক্ষতি", noDamage: "কোনও ক্ষতি নেই", locationAddress: "অবস্থানের ঠিকানা", gpsCoordinates: "GPS স্থানাঙ্ক", whatNext: "এরপর কী হবে?", nextDescription: "AI ফলাফল, GPS স্থানাঙ্ক ও রাস্তার ঠিকানা অভিযোগ হিসেবে সংরক্ষিত হবে। অনুমোদিত সরকারি কর্মকর্তারা অবস্থান যাচাই করে মেরামতের অবস্থা আপডেট করতে পারবেন।", gpsUnsupported: "এই ব্রাউজারে GPS সমর্থিত নয়।", gettingGps: "নির্ভুল GPS অবস্থান নেওয়া হচ্ছে...", locationCaptured: "অবস্থান পাওয়া গেছে", permissionDenied: "অবস্থানের অনুমতি প্রত্যাখ্যাত হয়েছে। অনুমতি দিয়ে আবার চেষ্টা করুন।", photoRequired: "রাস্তার ছবি তুলুন বা একটি ছবি বেছে নিন।", needGps: "অভিযোগ নথিভুক্ত করার আগে আপনার GPS অবস্থান প্রয়োজন।", analyzingMessage: "AI রাস্তার ছবি বিশ্লেষণ করে আপনার রিপোর্ট নথিভুক্ত করছে...", noDamageFound: "সমর্থিত রাস্তার ক্ষতি শনাক্ত হয়নি। আরও পরিষ্কার ছবি চেষ্টা করুন।", complaintSubmitted: "অভিযোগ সফলভাবে জমা হয়েছে" },
  Marathi: { citizenReporting: "नागरिक अहवाल", heroTitle: "रस्ता खराब आहे? एका मिनिटात अहवाल द्या.", heroDescription: "फोनवरून फोटो घ्या, GPS परवानगी द्या आणि आमचे AI खड्डे, भेगा व मॅनहोल ओळखेल.", step1: "रस्त्याचा फोटो घ्या", step2: "GPS ठिकाण जोडेल", step3: "AI नुकसान ओळखेल", step4: "तक्रार अधिकाऱ्यांपर्यंत पोहोचेल", newComplaint: "नवीन तक्रार", reportRoadDamage: "रस्त्याच्या नुकसानीचा अहवाल द्या", locationAttached: "अधिकाऱ्यांना रस्ता शोधता यावा म्हणून तुमचे ठिकाण या अहवालासोबत जोडले आहे.", takePhoto: "रस्त्याचा फोटो घ्या", cameraHint: "समर्थित फोनवर कॅमेरा उघडेल", gallery: "गॅलरीमधून निवडा", currentLocation: "📍 तुमचे सध्याचे ठिकाण", refreshGps: "GPS रिफ्रेश करा", locationNotCaptured: "ठिकाण अद्याप मिळालेले नाही", coordinatesSent: "रस्ता पडताळणीसाठी निर्देशांक फोटोसोबत पाठवले जातील.", submit: "🚨 नुकसान ओळखा आणि तक्रार नोंदवा", analyzing: "🤖 AI विश्लेषण करत आहे...", complaintRegistered: "तक्रार नोंदवली", reportReceived: "अहवाल प्राप्त झाला", detectedDamage: "आढळलेले नुकसान", noDamage: "नुकसान नाही", locationAddress: "ठिकाणाचा पत्ता", gpsCoordinates: "GPS निर्देशांक", whatNext: "पुढे काय होईल?", nextDescription: "AI निकाल, GPS निर्देशांक आणि रस्त्याचा पत्ता तक्रार म्हणून साठवला जाईल. अधिकृत अधिकारी ठिकाणाची पडताळणी करून दुरुस्तीची स्थिती अपडेट करू शकतात.", gpsUnsupported: "या ब्राउझरमध्ये GPS समर्थित नाही.", gettingGps: "अचूक GPS ठिकाण मिळवत आहे...", locationCaptured: "ठिकाण मिळाले", permissionDenied: "ठिकाणाची परवानगी नाकारली. परवानगी देऊन पुन्हा प्रयत्न करा.", photoRequired: "कृपया रस्त्याचा फोटो घ्या किंवा चित्र निवडा.", needGps: "तक्रार नोंदवण्यापूर्वी तुमचे GPS ठिकाण आवश्यक आहे.", analyzingMessage: "AI रस्त्याच्या फोटोचे विश्लेषण करून तुमचा अहवाल नोंदवत आहे...", noDamageFound: "समर्थित रस्त्याचे नुकसान आढळले नाही. अधिक स्पष्ट फोटो वापरा.", complaintSubmitted: "तक्रार यशस्वीपणे नोंदवली" },
  Telugu: { citizenReporting: "పౌరుల నివేదిక", heroTitle: "రోడ్డు దెబ్బతిన్నదా? ఒక నిమిషంలో నివేదించండి.", heroDescription: "ఫోన్‌తో ఫోటో తీసి, GPS అనుమతి ఇవ్వండి. మా AI గుంతలు, పగుళ్లు, మ్యాన్‌హోల్‌లను గుర్తిస్తుంది.", step1: "రోడ్డు ఫోటో తీయండి", step2: "GPS స్థానం జోడిస్తుంది", step3: "AI నష్టాన్ని గుర్తిస్తుంది", step4: "ఫిర్యాదు అధికారులకు చేరుతుంది", newComplaint: "కొత్త ఫిర్యాదు", reportRoadDamage: "రోడ్డు నష్టాన్ని నివేదించండి", locationAttached: "అధికారులు రోడ్డును కనుగొనడానికి మీ స్థానం ఈ నివేదికకు జోడించబడింది.", takePhoto: "రోడ్డు ఫోటో తీయండి", cameraHint: "మద్దతు ఉన్న ఫోన్లలో కెమెరా తెరుచుకుంటుంది", gallery: "గ్యాలరీ నుండి ఎంచుకోండి", currentLocation: "📍 మీ ప్రస్తుత స్థానం", refreshGps: "GPS రిఫ్రెష్ చేయండి", locationNotCaptured: "స్థానం ఇంకా పొందలేదు", coordinatesSent: "రోడ్డు ధృవీకరణ కోసం కోఆర్డినేట్లు చిత్రంతో పంపబడతాయి.", submit: "🚨 నష్టాన్ని గుర్తించి ఫిర్యాదు నమోదు చేయండి", analyzing: "🤖 AI విశ్లేషిస్తోంది...", complaintRegistered: "ఫిర్యాదు నమోదు చేయబడింది", reportReceived: "నివేదిక అందింది", detectedDamage: "గుర్తించిన నష్టం", noDamage: "నష్టం లేదు", locationAddress: "స్థాన చిరునామా", gpsCoordinates: "GPS కోఆర్డినేట్లు", whatNext: "తర్వాత ఏమి జరుగుతుంది?", nextDescription: "AI ఫలితం, GPS కోఆర్డినేట్లు మరియు రోడ్డు చిరునామా ఫిర్యాదుగా భద్రపరచబడతాయి. అధీకృత అధికారులు స్థానాన్ని ధృవీకరించి మరమ్మతు స్థితిని నవీకరించగలరు.", gpsUnsupported: "ఈ బ్రౌజర్‌లో GPSకు మద్దతు లేదు.", gettingGps: "ఖచ్చితమైన GPS స్థానం పొందుతోంది...", locationCaptured: "స్థానం పొందబడింది", permissionDenied: "స్థాన అనుమతి నిరాకరించబడింది. అనుమతించి మళ్లీ ప్రయత్నించండి.", photoRequired: "దయచేసి రోడ్డు ఫోటో తీయండి లేదా చిత్రాన్ని ఎంచుకోండి.", needGps: "ఫిర్యాదు నమోదు చేయడానికి ముందు మీ GPS స్థానం అవసరం.", analyzingMessage: "AI రోడ్డు చిత్రాన్ని విశ్లేషించి మీ నివేదికను నమోదు చేస్తోంది...", noDamageFound: "మద్దతు ఉన్న రోడ్డు నష్టం గుర్తించబడలేదు. స్పష్టమైన చిత్రాన్ని ప్రయత్నించండి.", complaintSubmitted: "ఫిర్యాదు విజయవంతంగా సమర్పించబడింది" },
  Tamil: { citizenReporting: "குடிமக்கள் அறிக்கை", heroTitle: "சாலை சேதமடைந்துள்ளதா? ஒரு நிமிடத்தில் புகாரளிக்கவும்.", heroDescription: "தொலைபேசியில் புகைப்படம் எடுத்து, GPS அனுமதி வழங்குங்கள். எங்கள் AI பள்ளங்கள், விரிசல்கள் மற்றும் மேன்ஹோல்களை கண்டறியும்.", step1: "சாலை புகைப்படம் எடுக்கவும்", step2: "GPS இடத்தை இணைக்கும்", step3: "AI சேதத்தை கண்டறியும்", step4: "புகார் அதிகாரியைச் சென்றடையும்", newComplaint: "புதிய புகார்", reportRoadDamage: "சாலை சேதத்தைப் புகாரளிக்கவும்", locationAttached: "அதிகாரிகள் சாலையைக் கண்டறிய உங்கள் இருப்பிடம் இந்தப் புகாருடன் இணைக்கப்பட்டுள்ளது.", takePhoto: "சாலை புகைப்படம் எடுக்கவும்", cameraHint: "ஆதரிக்கப்படும் தொலைபேசிகளில் கேமரா திறக்கும்", gallery: "கேலரியில் இருந்து தேர்வு செய்யவும்", currentLocation: "📍 உங்கள் தற்போதைய இருப்பிடம்", refreshGps: "GPS புதுப்பிக்கவும்", locationNotCaptured: "இருப்பிடம் இன்னும் பெறப்படவில்லை", coordinatesSent: "சாலை சரிபார்ப்புக்காக ஆயத்தொலைவுகள் படத்துடன் அனுப்பப்படும்.", submit: "🚨 சேதத்தைக் கண்டறிந்து புகாரைப் பதிவு செய்யவும்", analyzing: "🤖 AI ஆய்வு செய்கிறது...", complaintRegistered: "புகார் பதிவு செய்யப்பட்டது", reportReceived: "அறிக்கை பெறப்பட்டது", detectedDamage: "கண்டறியப்பட்ட சேதம்", noDamage: "சேதம் இல்லை", locationAddress: "இருப்பிட முகவரி", gpsCoordinates: "GPS ஆயத்தொலைவுகள்", whatNext: "அடுத்து என்ன நடக்கும்?", nextDescription: "AI முடிவு, GPS ஆயத்தொலைவுகள் மற்றும் சாலை முகவரி புகாராக சேமிக்கப்படும். அங்கீகரிக்கப்பட்ட அதிகாரிகள் இருப்பிடத்தைச் சரிபார்த்து பழுதுபார்ப்பு நிலையைப் புதுப்பிக்கலாம்.", gpsUnsupported: "இந்த உலாவியில் GPS ஆதரிக்கப்படவில்லை.", gettingGps: "துல்லியமான GPS இருப்பிடம் பெறப்படுகிறது...", locationCaptured: "இருப்பிடம் பெறப்பட்டது", permissionDenied: "இருப்பிட அனுமதி மறுக்கப்பட்டது. அனுமதித்து மீண்டும் முயற்சிக்கவும்.", photoRequired: "சாலை புகைப்படம் எடுக்கவும் அல்லது படத்தைத் தேர்வு செய்யவும்.", needGps: "புகாரைப் பதிவு செய்வதற்கு முன் உங்கள் GPS இருப்பிடம் தேவை.", analyzingMessage: "AI சாலைப் படத்தை ஆய்வு செய்து உங்கள் அறிக்கையைப் பதிவு செய்கிறது...", noDamageFound: "ஆதரிக்கப்படும் சாலை சேதம் கண்டறியப்படவில்லை. தெளிவான படத்தை முயற்சிக்கவும்.", complaintSubmitted: "புகார் வெற்றிகரமாக சமர்ப்பிக்கப்பட்டது" },
  Gujarati: { citizenReporting: "નાગરિક અહેવાલ", heroTitle: "રસ્તો ખરાબ છે? એક મિનિટમાં અહેવાલ આપો.", heroDescription: "ફોનથી ફોટો લો, GPSની પરવાનગી આપો અને અમારું AI ખાડા, તિરાડો અને મેનહોલ ઓળખશે.", step1: "રસ્તાનો ફોટો લો", step2: "GPS સ્થાન જોડશે", step3: "AI નુકસાન ઓળખશે", step4: "ફરિયાદ અધિકારી સુધી પહોંચશે", newComplaint: "નવી ફરિયાદ", reportRoadDamage: "રસ્તાના નુકસાનની જાણ કરો", locationAttached: "અધિકારી રસ્તો શોધી શકે તે માટે તમારું સ્થાન આ અહેવાલ સાથે જોડવામાં આવ્યું છે.", takePhoto: "રસ્તાનો ફોટો લો", cameraHint: "સમર્થિત ફોનમાં કેમેરા ખુલશે", gallery: "ગેલેરીમાંથી પસંદ કરો", currentLocation: "📍 તમારું વર્તમાન સ્થાન", refreshGps: "GPS રિફ્રેશ કરો", locationNotCaptured: "સ્થાન હજી મળ્યું નથી", coordinatesSent: "રસ્તાની ચકાસણી માટે કોઓર્ડિનેટ્સ છબી સાથે મોકલવામાં આવશે.", submit: "🚨 નુકસાન ઓળખો અને ફરિયાદ નોંધાવો", analyzing: "🤖 AI તપાસ કરી રહ્યું છે...", complaintRegistered: "ફરિયાદ નોંધાઈ", reportReceived: "અહેવાલ મળ્યો", detectedDamage: "ઓળખાયેલું નુકસાન", noDamage: "નુકસાન નથી", locationAddress: "સ્થાનનું સરનામું", gpsCoordinates: "GPS કોઓર્ડિનેટ્સ", whatNext: "હવે આગળ શું થશે?", nextDescription: "AI પરિણામ, GPS કોઓર્ડિનેટ્સ અને રસ્તાનું સરનામું ફરિયાદ તરીકે સંગ્રહિત થશે. અધિકૃત અધિકારીઓ સ્થાન ચકાસી અને સમારકામની સ્થિતિ અપડેટ કરી શકે છે.", gpsUnsupported: "આ બ્રાઉઝરમાં GPS સપોર્ટેડ નથી.", gettingGps: "ચોક્કસ GPS સ્થાન મેળવી રહ્યા છીએ...", locationCaptured: "સ્થાન મળ્યું", permissionDenied: "સ્થાનની પરવાનગી નકારી. પરવાનગી આપીને ફરી પ્રયાસ કરો.", photoRequired: "કૃપા કરીને રસ્તાનો ફોટો લો અથવા છબી પસંદ કરો.", needGps: "ફરિયાદ નોંધાવતા પહેલાં તમારું GPS સ્થાન જરૂરી છે.", analyzingMessage: "AI રસ્તાની છબીનું વિશ્લેષણ કરીને તમારો અહેવાલ નોંધે છે...", noDamageFound: "સમર્થિત રસ્તાનું નુકસાન મળ્યું નથી. વધુ સ્પષ્ટ છબી અજમાવો.", complaintSubmitted: "ફરિયાદ સફળતાપૂર્વક નોંધાઈ" },
  Kannada: { citizenReporting: "ನಾಗರಿಕ ವರದಿ", heroTitle: "ರಸ್ತೆ ಹಾಳಾಗಿದೆಯೇ? ಒಂದು ನಿಮಿಷದಲ್ಲಿ ವರದಿ ಮಾಡಿ.", heroDescription: "ಫೋನ್‌ನಲ್ಲಿ ಚಿತ್ರ ತೆಗೆದು GPS ಅನುಮತಿ ನೀಡಿ. ನಮ್ಮ AI ಗುಂಡಿಗಳು, ಬಿರುಕುಗಳು ಮತ್ತು ಮ್ಯಾನ್‌ಹೋಲ್‌ಗಳನ್ನು ಗುರುತಿಸುತ್ತದೆ.", step1: "ರಸ್ತೆಯ ಚಿತ್ರ ತೆಗೆದುಕೊಳ್ಳಿ", step2: "GPS ಸ್ಥಳ ಸೇರಿಸುತ್ತದೆ", step3: "AI ಹಾನಿ ಗುರುತಿಸುತ್ತದೆ", step4: "ದೂರು ಅಧಿಕಾರಿಗಳನ್ನು ತಲುಪುತ್ತದೆ", newComplaint: "ಹೊಸ ದೂರು", reportRoadDamage: "ರಸ್ತೆ ಹಾನಿ ವರದಿ ಮಾಡಿ", locationAttached: "ಅಧಿಕಾರಿಗಳು ರಸ್ತೆಯನ್ನು ಹುಡುಕಲು ನಿಮ್ಮ ಸ್ಥಳವನ್ನು ಈ ವರದಿಗೆ ಸೇರಿಸಲಾಗಿದೆ.", takePhoto: "ರಸ್ತೆಯ ಚಿತ್ರ ತೆಗೆದುಕೊಳ್ಳಿ", cameraHint: "ಬೆಂಬಲಿತ ಫೋನ್‌ಗಳಲ್ಲಿ ಕ್ಯಾಮೆರಾ ತೆರೆಯುತ್ತದೆ", gallery: "ಗ್ಯಾಲರಿಯಿಂದ ಆಯ್ಕೆ ಮಾಡಿ", currentLocation: "📍 ನಿಮ್ಮ ಪ್ರಸ್ತುತ ಸ್ಥಳ", refreshGps: "GPS ರಿಫ್ರೆಶ್ ಮಾಡಿ", locationNotCaptured: "ಸ್ಥಳ ಇನ್ನೂ ಪಡೆಯಲಾಗಿಲ್ಲ", coordinatesSent: "ರಸ್ತೆ ಪರಿಶೀಲನೆಗಾಗಿ ನಿರ್ದೇಶಾಂಕಗಳನ್ನು ಚಿತ್ರದೊಂದಿಗೆ ಕಳುಹಿಸಲಾಗುತ್ತದೆ.", submit: "🚨 ಹಾನಿ ಪತ್ತೆಹಚ್ಚಿ ದೂರು ದಾಖಲಿಸಿ", analyzing: "🤖 AI ಪರಿಶೀಲಿಸುತ್ತಿದೆ...", complaintRegistered: "ದೂರು ದಾಖಲಾಗಿದೆ", reportReceived: "ವರದಿ ಸ್ವೀಕರಿಸಲಾಗಿದೆ", detectedDamage: "ಪತ್ತೆಯಾದ ಹಾನಿ", noDamage: "ಹಾನಿ ಇಲ್ಲ", locationAddress: "ಸ್ಥಳದ ವಿಳಾಸ", gpsCoordinates: "GPS ನಿರ್ದೇಶಾಂಕಗಳು", whatNext: "ಮುಂದೇನು?", nextDescription: "AI ಫಲಿತಾಂಶ, GPS ನಿರ್ದೇಶಾಂಕಗಳು ಮತ್ತು ರಸ್ತೆ ವಿಳಾಸವನ್ನು ದೂರುವಾಗಿ ಉಳಿಸಲಾಗುತ್ತದೆ. ಅಧಿಕೃತ ಅಧಿಕಾರಿಗಳು ಸ್ಥಳ ಪರಿಶೀಲಿಸಿ ದುರಸ್ತಿ ಸ್ಥಿತಿಯನ್ನು ನವೀಕರಿಸಬಹುದು.", gpsUnsupported: "ಈ ಬ್ರೌಸರ್ GPS ಅನ್ನು ಬೆಂಬಲಿಸುವುದಿಲ್ಲ.", gettingGps: "ನಿಖರ GPS ಸ್ಥಳ ಪಡೆಯಲಾಗುತ್ತಿದೆ...", locationCaptured: "ಸ್ಥಳ ಪಡೆಯಲಾಗಿದೆ", permissionDenied: "ಸ್ಥಳ ಅನುಮತಿ ನಿರಾಕರಿಸಲಾಗಿದೆ. ಅನುಮತಿಸಿ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.", photoRequired: "ರಸ್ತೆಯ ಚಿತ್ರ ತೆಗೆದುಕೊಳ್ಳಿ ಅಥವಾ ಚಿತ್ರವನ್ನು ಆಯ್ಕೆ ಮಾಡಿ.", needGps: "ದೂರು ದಾಖಲಿಸುವ ಮೊದಲು ನಿಮ್ಮ GPS ಸ್ಥಳ ಅಗತ್ಯವಿದೆ.", analyzingMessage: "AI ರಸ್ತೆ ಚಿತ್ರವನ್ನು ವಿಶ್ಲೇಷಿಸಿ ನಿಮ್ಮ ವರದಿಯನ್ನು ದಾಖಲಿಸುತ್ತಿದೆ...", noDamageFound: "ಬೆಂಬಲಿತ ರಸ್ತೆ ಹಾನಿ ಕಂಡುಬಂದಿಲ್ಲ. ಸ್ಪಷ್ಟವಾದ ಚಿತ್ರ ಪ್ರಯತ್ನಿಸಿ.", complaintSubmitted: "ದೂರು ಯಶಸ್ವಿಯಾಗಿ ಸಲ್ಲಿಸಲಾಗಿದೆ" },
  Malayalam: { citizenReporting: "പൗര റിപ്പോർട്ടിംഗ്", heroTitle: "റോഡ് തകർന്നോ? ഒരു മിനിറ്റിൽ റിപ്പോർട്ട് ചെയ്യൂ.", heroDescription: "ഫോണിൽ നിന്ന് ചിത്രം എടുക്കുക, GPS അനുമതി നൽകുക. ഞങ്ങളുടെ AI കുഴികളും വിള്ളലുകളും മാൻഹോളുകളും കണ്ടെത്തും.", step1: "റോഡിന്റെ ചിത്രം എടുക്കുക", step2: "GPS സ്ഥാനം ചേർക്കും", step3: "AI കേടുപാട് കണ്ടെത്തും", step4: "പരാതി അധികാരികളിലെത്തും", newComplaint: "പുതിയ പരാതി", reportRoadDamage: "റോഡ് കേടുപാട് റിപ്പോർട്ട് ചെയ്യുക", locationAttached: "അധികാരികൾക്ക് റോഡ് കണ്ടെത്താൻ നിങ്ങളുടെ സ്ഥലം ഈ റിപ്പോർട്ടിനൊപ്പം ചേർത്തിട്ടുണ്ട്.", takePhoto: "റോഡിന്റെ ചിത്രം എടുക്കുക", cameraHint: "പിന്തുണയുള്ള ഫോണുകളിൽ ക്യാമറ തുറക്കും", gallery: "ഗാലറിയിൽ നിന്ന് തിരഞ്ഞെടുക്കുക", currentLocation: "📍 നിങ്ങളുടെ നിലവിലെ സ്ഥലം", refreshGps: "GPS പുതുക്കുക", locationNotCaptured: "സ്ഥലം ഇതുവരെ ലഭിച്ചിട്ടില്ല", coordinatesSent: "റോഡ് പരിശോധനയ്ക്കായി കോർഡിനേറ്റുകൾ ചിത്രത്തോടൊപ്പം അയയ്ക്കും.", submit: "🚨 കേടുപാട് കണ്ടെത്തി പരാതി രജിസ്റ്റർ ചെയ്യുക", analyzing: "🤖 AI പരിശോധിക്കുന്നു...", complaintRegistered: "പരാതി രജിസ്റ്റർ ചെയ്തു", reportReceived: "റിപ്പോർട്ട് ലഭിച്ചു", detectedDamage: "കണ്ടെത്തിയ കേടുപാട്", noDamage: "കേടുപാടില്ല", locationAddress: "സ്ഥല വിലാസം", gpsCoordinates: "GPS കോർഡിനേറ്റുകൾ", whatNext: "അടുത്തത് എന്ത്?", nextDescription: "AI ഫലം, GPS കോർഡിനേറ്റുകൾ, റോഡ് വിലാസം എന്നിവ പരാതിയായി സൂക്ഷിക്കും. അധികാരപ്പെട്ട ഉദ്യോഗസ്ഥർ സ്ഥലം പരിശോധിച്ച് അറ്റകുറ്റപ്പണി നില പുതുക്കും.", gpsUnsupported: "ഈ ബ്രൗസറിൽ GPS പിന്തുണയ്ക്കുന്നില്ല.", gettingGps: "കൃത്യമായ GPS സ്ഥലം നേടുന്നു...", locationCaptured: "സ്ഥലം ലഭിച്ചു", permissionDenied: "സ്ഥലാനുമതി നിഷേധിച്ചു. അനുമതി നൽകി വീണ്ടും ശ്രമിക്കുക.", photoRequired: "റോഡിന്റെ ചിത്രം എടുക്കുക അല്ലെങ്കിൽ ചിത്രം തിരഞ്ഞെടുക്കുക.", needGps: "പരാതി രജിസ്റ്റർ ചെയ്യുന്നതിന് മുമ്പ് നിങ്ങളുടെ GPS സ്ഥലം ആവശ്യമാണ്.", analyzingMessage: "AI റോഡ് ചിത്രം പരിശോധിച്ച് നിങ്ങളുടെ റിപ്പോർട്ട് രജിസ്റ്റർ ചെയ്യുന്നു...", noDamageFound: "പിന്തുണയ്ക്കുന്ന റോഡ് കേടുപാട് കണ്ടെത്തിയില്ല. കൂടുതൽ വ്യക്തമായ ചിത്രം ശ്രമിക്കുക.", complaintSubmitted: "പരാതി വിജയകരമായി സമർപ്പിച്ചു" },
  Punjabi: { citizenReporting: "ਨਾਗਰਿਕ ਰਿਪੋਰਟਿੰਗ", heroTitle: "ਸੜਕ ਖਰਾਬ ਹੈ? ਇੱਕ ਮਿੰਟ ਵਿੱਚ ਰਿਪੋਰਟ ਕਰੋ।", heroDescription: "ਫੋਨ ਨਾਲ ਤਸਵੀਰ ਲਓ, GPS ਦੀ ਇਜਾਜ਼ਤ ਦਿਓ ਅਤੇ ਸਾਡਾ AI ਟੋਏ, ਦਰਾਰਾਂ ਅਤੇ ਮੈਨਹੋਲ ਪਛਾਣੇਗਾ।", step1: "ਸੜਕ ਦੀ ਤਸਵੀਰ ਲਓ", step2: "GPS ਸਥਾਨ ਜੋੜੇਗਾ", step3: "AI ਨੁਕਸਾਨ ਪਛਾਣੇਗਾ", step4: "ਸ਼ਿਕਾਇਤ ਅਧਿਕਾਰੀ ਤੱਕ ਪਹੁੰਚੇਗੀ", newComplaint: "ਨਵੀਂ ਸ਼ਿਕਾਇਤ", reportRoadDamage: "ਸੜਕ ਦੇ ਨੁਕਸਾਨ ਦੀ ਰਿਪੋਰਟ ਕਰੋ", locationAttached: "ਅਧਿਕਾਰੀ ਸੜਕ ਲੱਭ ਸਕਣ, ਇਸ ਲਈ ਤੁਹਾਡਾ ਸਥਾਨ ਰਿਪੋਰਟ ਨਾਲ ਜੋੜਿਆ ਗਿਆ ਹੈ।", takePhoto: "ਸੜਕ ਦੀ ਤਸਵੀਰ ਲਓ", cameraHint: "ਸਮਰਥਿਤ ਫੋਨਾਂ ਵਿੱਚ ਕੈਮਰਾ ਖੁੱਲ੍ਹੇਗਾ", gallery: "ਗੈਲਰੀ ਵਿੱਚੋਂ ਚੁਣੋ", currentLocation: "📍 ਤੁਹਾਡਾ ਮੌਜੂਦਾ ਸਥਾਨ", refreshGps: "GPS ਤਾਜ਼ਾ ਕਰੋ", locationNotCaptured: "ਸਥਾਨ ਅਜੇ ਨਹੀਂ ਮਿਲਿਆ", coordinatesSent: "ਸੜਕ ਦੀ ਜਾਂਚ ਲਈ ਕੋਆਰਡੀਨੇਟ ਤਸਵੀਰ ਨਾਲ ਭੇਜੇ ਜਾਣਗੇ।", submit: "🚨 ਨੁਕਸਾਨ ਪਛਾਣੋ ਅਤੇ ਸ਼ਿਕਾਇਤ ਦਰਜ ਕਰੋ", analyzing: "🤖 AI ਜਾਂਚ ਕਰ ਰਿਹਾ ਹੈ...", complaintRegistered: "ਸ਼ਿਕਾਇਤ ਦਰਜ ਹੋ ਗਈ", reportReceived: "ਰਿਪੋਰਟ ਮਿਲ ਗਈ", detectedDamage: "ਪਛਾਣਿਆ ਨੁਕਸਾਨ", noDamage: "ਕੋਈ ਨੁਕਸਾਨ ਨਹੀਂ", locationAddress: "ਸਥਾਨ ਦਾ ਪਤਾ", gpsCoordinates: "GPS ਕੋਆਰਡੀਨੇਟ", whatNext: "ਅੱਗੇ ਕੀ ਹੋਵੇਗਾ?", nextDescription: "AI ਨਤੀਜਾ, GPS ਕੋਆਰਡੀਨੇਟ ਅਤੇ ਸੜਕ ਦਾ ਪਤਾ ਸ਼ਿਕਾਇਤ ਵਜੋਂ ਸੁਰੱਖਿਅਤ ਹੋਵੇਗਾ। ਅਧਿਕਾਰੀ ਸਥਾਨ ਦੀ ਜਾਂਚ ਕਰਕੇ ਮੁਰੰਮਤ ਦੀ ਸਥਿਤੀ ਬਦਲ ਸਕਦੇ ਹਨ।", gpsUnsupported: "ਇਸ ਬ੍ਰਾਊਜ਼ਰ ਵਿੱਚ GPS ਸਮਰਥਿਤ ਨਹੀਂ ਹੈ।", gettingGps: "ਸਹੀ GPS ਸਥਾਨ ਲਿਆ ਜਾ ਰਿਹਾ ਹੈ...", locationCaptured: "ਸਥਾਨ ਮਿਲ ਗਿਆ", permissionDenied: "ਸਥਾਨ ਦੀ ਇਜਾਜ਼ਤ ਰੱਦ ਹੋਈ। ਇਜਾਜ਼ਤ ਦੇ ਕੇ ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ।", photoRequired: "ਕਿਰਪਾ ਕਰਕੇ ਸੜਕ ਦੀ ਤਸਵੀਰ ਲਓ ਜਾਂ ਚਿੱਤਰ ਚੁਣੋ।", needGps: "ਸ਼ਿਕਾਇਤ ਦਰਜ ਕਰਨ ਤੋਂ ਪਹਿਲਾਂ ਤੁਹਾਡਾ GPS ਸਥਾਨ ਲਾਜ਼ਮੀ ਹੈ।", analyzingMessage: "AI ਸੜਕ ਦੀ ਤਸਵੀਰ ਦੀ ਜਾਂਚ ਕਰਕੇ ਤੁਹਾਡੀ ਰਿਪੋਰਟ ਦਰਜ ਕਰ ਰਿਹਾ ਹੈ...", noDamageFound: "ਸੜਕ ਦਾ ਕੋਈ ਸਮਰਥਿਤ ਨੁਕਸਾਨ ਨਹੀਂ ਮਿਲਿਆ। ਹੋਰ ਸਾਫ਼ ਤਸਵੀਰ ਅਜ਼ਮਾਓ।", complaintSubmitted: "ਸ਼ਿਕਾਇਤ ਸਫਲਤਾਪੂਰਵਕ ਦਰਜ ਹੋਈ" },
  Urdu: { citizenReporting: "شہری رپورٹنگ", heroTitle: "سڑک خراب ہے؟ ایک منٹ میں رپورٹ کریں۔", heroDescription: "فون سے تصویر لیں، GPS کی اجازت دیں اور ہمارا AI گڑھے، دراڑیں اور مین ہولز کی شناخت کرے گا۔", step1: "سڑک کی تصویر لیں", step2: "GPS مقام شامل کرے گا", step3: "AI نقصان کی شناخت کرے گا", step4: "شکایت افسر تک پہنچے گی", newComplaint: "نئی شکایت", reportRoadDamage: "سڑک کے نقصان کی رپورٹ کریں", locationAttached: "افسر سڑک تلاش کر سکیں، اس لیے آپ کا مقام اس رپورٹ کے ساتھ شامل کیا گیا ہے۔", takePhoto: "سڑک کی تصویر لیں", cameraHint: "معاون فون پر کیمرا کھلے گا", gallery: "گیلری سے منتخب کریں", currentLocation: "📍 آپ کا موجودہ مقام", refreshGps: "GPS تازہ کریں", locationNotCaptured: "مقام ابھی حاصل نہیں ہوا", coordinatesSent: "سڑک کی تصدیق کے لیے کوآرڈینیٹس تصویر کے ساتھ بھیجے جائیں گے۔", submit: "🚨 نقصان کی شناخت کرکے شکایت درج کریں", analyzing: "🤖 AI تجزیہ کر رہا ہے...", complaintRegistered: "شکایت درج ہو گئی", reportReceived: "رپورٹ موصول ہوئی", detectedDamage: "شناخت شدہ نقصان", noDamage: "کوئی نقصان نہیں", locationAddress: "مقام کا پتہ", gpsCoordinates: "GPS کوآرڈینیٹس", whatNext: "اب آگے کیا ہوگا؟", nextDescription: "AI نتیجہ، GPS کوآرڈینیٹس اور سڑک کا پتہ شکایت کے طور پر محفوظ کیا جائے گا۔ مجاز افسر مقام کی تصدیق کرکے مرمت کی حالت اپ ڈیٹ کر سکتے ہیں۔", gpsUnsupported: "اس براؤزر میں GPS معاونت موجود نہیں ہے۔", gettingGps: "درست GPS مقام حاصل کیا جا رہا ہے...", locationCaptured: "مقام حاصل ہو گیا", permissionDenied: "مقام کی اجازت مسترد کر دی گئی۔ اجازت دے کر دوبارہ کوشش کریں۔", photoRequired: "براہ کرم سڑک کی تصویر لیں یا تصویر منتخب کریں۔", needGps: "شکایت درج کرنے سے پہلے آپ کا GPS مقام ضروری ہے۔", analyzingMessage: "AI سڑک کی تصویر کا تجزیہ کرکے آپ کی رپورٹ درج کر رہا ہے...", noDamageFound: "سڑک کا کوئی معاون نقصان نہیں ملا۔ زیادہ واضح تصویر آزمائیں۔", complaintSubmitted: "شکایت کامیابی سے درج ہو گئی" },
  Odia: { citizenReporting: "ନାଗରିକ ରିପୋର୍ଟ", heroTitle: "ରାସ୍ତା ଖରାପ? ଏକ ମିନିଟରେ ରିପୋର୍ଟ କରନ୍ତୁ।", heroDescription: "ଫୋନରେ ଫଟୋ ନିଅନ୍ତୁ, GPS ଅନୁମତି ଦିଅନ୍ତୁ ଏବଂ ଆମ AI ଖାଲ, ଫାଟ ଓ ମ୍ୟାନହୋଲ ଚିହ୍ନଟ କରିବ।", step1: "ରାସ୍ତାର ଫଟୋ ନିଅନ୍ତୁ", step2: "GPS ସ୍ଥାନ ଯୋଡ଼ିବ", step3: "AI କ୍ଷତି ଚିହ୍ନଟ କରିବ", step4: "ଅଭିଯୋଗ କର୍ତ୍ତୃପକ୍ଷଙ୍କ ପାଖକୁ ଯିବ", newComplaint: "ନୂଆ ଅଭିଯୋଗ", reportRoadDamage: "ରାସ୍ତା କ୍ଷତି ରିପୋର୍ଟ କରନ୍ତୁ", locationAttached: "କର୍ତ୍ତୃପକ୍ଷ ରାସ୍ତା ଖୋଜି ପାରିବେ ବୋଲି ଆପଣଙ୍କ ସ୍ଥାନ ଏହି ରିପୋର୍ଟ ସହ ଯୋଡ଼ାଯାଇଛି।", takePhoto: "ରାସ୍ତାର ଫଟୋ ନିଅନ୍ତୁ", cameraHint: "ସମର୍ଥିତ ଫୋନରେ କ୍ୟାମେରା ଖୋଲିବ", gallery: "ଗ୍ୟାଲେରୀରୁ ବାଛନ୍ତୁ", currentLocation: "📍 ଆପଣଙ୍କ ବର୍ତ୍ତମାନ ସ୍ଥାନ", refreshGps: "GPS ରିଫ୍ରେଶ କରନ୍ତୁ", locationNotCaptured: "ସ୍ଥାନ ଏପର୍ଯ୍ୟନ୍ତ ମିଳିନାହିଁ", coordinatesSent: "ରାସ୍ତା ଯାଞ୍ଚ ପାଇଁ ନିର୍ଦ୍ଦେଶାଙ୍କ ଚିତ୍ର ସହ ପଠାଯିବ।", submit: "🚨 କ୍ଷତି ଚିହ୍ନଟ କରି ଅଭିଯୋଗ ଦାଖଲ କରନ୍ତୁ", analyzing: "🤖 AI ଯାଞ୍ଚ କରୁଛି...", complaintRegistered: "ଅଭିଯୋଗ ଦାଖଲ ହୋଇଛି", reportReceived: "ରିପୋର୍ଟ ମିଳିଛି", detectedDamage: "ଚିହ୍ନଟ କ୍ଷତି", noDamage: "କୌଣସି କ୍ଷତି ନାହିଁ", locationAddress: "ସ୍ଥାନ ଠିକଣା", gpsCoordinates: "GPS ନିର୍ଦ୍ଦେଶାଙ୍କ", whatNext: "ପରେ କଣ ହେବ?", nextDescription: "AI ଫଳାଫଳ, GPS ନିର୍ଦ୍ଦେଶାଙ୍କ ଏବଂ ରାସ୍ତା ଠିକଣା ଅଭିଯୋଗ ଭାବରେ ସଂରକ୍ଷିତ ହେବ। ଅଧିକୃତ ଅଧିକାରୀ ସ୍ଥାନ ଯାଞ୍ଚ କରି ମରାମତି ସ୍ଥିତି ଅପଡେଟ କରିପାରିବେ।", gpsUnsupported: "ଏହି ବ୍ରାଉଜରରେ GPS ସମର୍ଥିତ ନୁହେଁ।", gettingGps: "ସଠିକ GPS ସ୍ଥାନ ନିଆଯାଉଛି...", locationCaptured: "ସ୍ଥାନ ମିଳିଛି", permissionDenied: "ସ୍ଥାନ ଅନୁମତି ମନା ହୋଇଛି। ଅନୁମତି ଦେଇ ପୁଣି ଚେଷ୍ଟା କରନ୍ତୁ।", photoRequired: "ଦୟାକରି ରାସ୍ତାର ଫଟୋ ନିଅନ୍ତୁ କିମ୍ବା ଚିତ୍ର ବାଛନ୍ତୁ।", needGps: "ଅଭିଯୋଗ ଦାଖଲ ପୂର୍ବରୁ ଆପଣଙ୍କ GPS ସ୍ଥାନ ଆବଶ୍ୟକ।", analyzingMessage: "AI ରାସ୍ତା ଚିତ୍ର ବିଶ୍ଳେଷଣ କରି ଆପଣଙ୍କ ରିପୋର୍ଟ ଦାଖଲ କରୁଛି...", noDamageFound: "ସମର୍ଥିତ ରାସ୍ତା କ୍ଷତି ମିଳିଲା ନାହିଁ। ଅଧିକ ସ୍ପଷ୍ଟ ଚିତ୍ର ଚେଷ୍ଟା କରନ୍ତୁ।", complaintSubmitted: "ଅଭିଯୋଗ ସଫଳତାର ସହ ଦାଖଲ ହୋଇଛି" },
};

const DAMAGE_LABELS = {
  English: { pothole: "Pothole", crack: "Crack", manhole: "Manhole" },
  Hindi: { pothole: "गड्ढा", crack: "दरार", manhole: "मैनहोल" },
  Bengali: { pothole: "গর্ত", crack: "ফাটল", manhole: "ম্যানহোল" },
  Marathi: { pothole: "खड्डा", crack: "भेग", manhole: "मॅनहोल" },
  Telugu: { pothole: "గుంత", crack: "పగులు", manhole: "మ్యాన్‌హోల్" },
  Tamil: { pothole: "பள்ளம்", crack: "விரிசல்", manhole: "மேன்ஹோல்" },
  Gujarati: { pothole: "ખાડો", crack: "તિરાડ", manhole: "મેનહોલ" },
  Kannada: { pothole: "ಗುಂಡಿ", crack: "ಬಿರುಕು", manhole: "ಮ್ಯಾನ್‌ಹೋಲ್" },
  Malayalam: { pothole: "കുഴി", crack: "വിള്ളൽ", manhole: "മാൻഹോൾ" },
  Punjabi: { pothole: "ਟੋਆ", crack: "ਦਰਾਰ", manhole: "ਮੈਨਹੋਲ" },
  Urdu: { pothole: "گڑھا", crack: "دراڑ", manhole: "مین ہول" },
  Odia: { pothole: "ଖାଲ", crack: "ଫାଟ", manhole: "ମ୍ୟାନହୋଲ" }
};

// Leaflet marker icons
try { delete L.Icon.Default.prototype._getIconUrl; } catch (_) {}
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png"
});

function App() {
  const [view, setView] = useState("citizen");
  const [citizenMode, setCitizenMode] = useState("live");
  const [govToken, setGovToken] = useState(() => localStorage.getItem("roadGovToken") || "");
  const [loginOpen, setLoginOpen] = useState(false);
  const [username, setUsername] = useState("gov_admin");
  const [password, setPassword] = useState("");
  const [loginMsg, setLoginMsg] = useState("");
  const [citizenLanguage, setCitizenLanguage] = useState("English");
  const [languageQuery, setLanguageQuery] = useState("");

  const [stats, setStats] = useState({});
  const [rows, setRows] = useState([]);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [latitude, setLatitude] = useState(null);
  const [longitude, setLongitude] = useState(null);
  const [locationAccuracy, setLocationAccuracy] = useState(null);
  const [manualAddress, setManualAddress] = useState("");
  const [locationStatus, setLocationStatus] = useState("Location not captured yet");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [result, setResult] = useState(null);
  const [complaintId, setComplaintId] = useState(null);
  const [offlineReports, setOfflineReports] = useState(() => JSON.parse(localStorage.getItem("roadOfflineReports") || "[]"));

  const isGov = Boolean(govToken);
  const translations = TRANSLATIONS[citizenLanguage] || ENGLISH;
  const damageLabels = DAMAGE_LABELS[citizenLanguage] || DAMAGE_LABELS.English;
  const t = key => translations[key] || ENGLISH[key];
  const ui = view === "citizen" ? t : key => ENGLISH[key];

  useEffect(() => {
    if (locationStatus === ENGLISH.locationNotCaptured || locationStatus === "Location not captured yet") {
      setLocationStatus(t("locationNotCaptured"));
    }
  }, [citizenLanguage]);

  useEffect(() => {
    if (govToken) loadGovernment();
  }, [govToken]);

  useEffect(() => {
    localStorage.setItem("roadOfflineReports", JSON.stringify(offlineReports));
  }, [offlineReports]);

  async function loadGovernment() {
    try {
      const headers = { Authorization: `Bearer ${govToken}` };
      const [s, r] = await Promise.all([
        fetch(API + "/api/dashboard/stats", { headers }),
        fetch(API + "/api/damages", { headers })
      ]);
      if (s.status === 401 || r.status === 401) return logout();
      setStats(await s.json());
      setRows(await r.json());
    } catch (_) {
      setLoginMsg("FastAPI backend is not reachable on port 8000.");
    }
  }

  function logout() {
    localStorage.removeItem("roadGovToken");
    setGovToken("");
    setView("citizen");
    setRows([]);
    setStats({});
  }

  async function governmentLogin(e) {
    e.preventDefault();
    setLoginMsg("Checking government credentials...");
    const fd = new FormData();
    fd.append("username", username);
    fd.append("password", password);
    try {
      const r = await fetch(API + "/api/government/login", { method: "POST", body: fd });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "Login failed");
      localStorage.setItem("roadGovToken", data.access_token);
      setGovToken(data.access_token);
      setLoginOpen(false);
      setPassword("");
      setLoginMsg("");
      setView("government");
    } catch (e) {
      setLoginMsg(e.message);
    }
  }

  function getLocation(useHighAccuracy = true) {
    if (!navigator.geolocation) {
      setLocationStatus(t("gpsUnsupported"));
      return;
    }
    setLocationStatus(t("gettingGps"));
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        setLatitude(lat);
        setLongitude(lng);
        const accuracy = position.coords.accuracy ? Math.round(position.coords.accuracy) : null;
        setLocationAccuracy(accuracy);
        setLocationStatus(`${t("locationCaptured")} • ${lat.toFixed(6)}, ${lng.toFixed(6)}${accuracy ? ` • ±${accuracy} m` : ""}`);
      },
      (error) => {
        if (error.code === error.PERMISSION_DENIED) {
          setLocationStatus(t("permissionDenied") + " " + t("permissionHelp"));
        } else if (useHighAccuracy && (error.code === error.POSITION_UNAVAILABLE || error.code === error.TIMEOUT)) {
          setLocationStatus(t("gettingGps"));
          getLocation(false);
        } else {
          setLocationStatus(t("gpsUnavailable"));
        }
      },
      { enableHighAccuracy: useHighAccuracy, timeout: useHighAccuracy ? 15000 : 30000, maximumAge: useHighAccuracy ? 0 : 60000 }
    );
  }

  function handleFile(e) {
    const selected = e.target.files?.[0];
    if (!selected) return;
    setFile(selected);
    setPreview(URL.createObjectURL(selected));
    setResult(null);
    if (citizenMode === "live") getLocation();
  }

  async function detect(e) {
    e.preventDefault();
    if (!file) return setMsg(t("photoRequired"));
    if (citizenMode === "offline") {
      if (!manualAddress.trim()) return setMsg("Add the road address before saving this offline report.");
      setBusy(true);
      try {
        const dataUrl = await fileToDataUrl(file);
        setOfflineReports(current => [...current, {
          id: crypto.randomUUID(),
          filename: file.name || "road-report.jpg",
          dataUrl,
          address: manualAddress.trim(),
          savedAt: new Date().toISOString(),
        }]);
        setFile(null);
        setPreview("");
        setMsg("Saved on this device. Sync it when you reach a network area.");
      } catch (_) {
        setMsg("Could not save the image on this device.");
      } finally {
        setBusy(false);
      }
      return;
    }
    if (latitude === null || longitude === null) {
      setMsg(t("needGps"));
      getLocation();
      return;
    }

    setBusy(true);
    setMsg(t("analyzingMessage"));
    const fd = new FormData();
    fd.append("file", file);
    fd.append("latitude", latitude);
    fd.append("longitude", longitude);
    if (manualAddress.trim()) fd.append("address_override", manualAddress.trim());
    if (locationAccuracy !== null) fd.append("location_accuracy_m", locationAccuracy);

    try {
      const r = await fetch(API + "/api/detect", { method: "POST", body: fd });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "Detection failed");
      setResult(data);
      setComplaintId(data.complaint_id ?? null);
      if (data.count === 0) {
        setMsg(t("noDamageFound"));
      } else if (data.linked_complaint_ids?.length) {
        setMsg(`Existing complaint linked • ID #${data.complaint_id}`);
      } else {
        setMsg(`${t("complaintSubmitted")} • ID #${data.complaint_id}`);
      }
      setFile(null);
      setPreview("");
    } catch (e) {
      setMsg(e.message || t("detectionFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function syncOfflineReports() {
    if (!offlineReports.length) return;
    if (latitude === null || longitude === null) {
      setMsg("Reach a network area, then capture GPS before syncing saved reports.");
      getLocation();
      return;
    }
    setBusy(true);
    let remaining = [...offlineReports];
    try {
      for (const saved of offlineReports) {
        const fd = new FormData();
        fd.append("file", dataUrlToFile(saved.dataUrl, saved.filename));
        fd.append("latitude", latitude);
        fd.append("longitude", longitude);
        fd.append("address_override", saved.address);
        const response = await fetch(API + "/api/detect", { method: "POST", body: fd });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Sync failed");
        remaining = remaining.filter(item => item.id !== saved.id);
      }
      setOfflineReports(remaining);
      setMsg("Saved reports synced successfully.");
    } catch (error) {
      setOfflineReports(remaining);
      setMsg(error.message || "Some saved reports could not be synced.");
    } finally {
      setBusy(false);
    }
  }

  async function status(id, value) {
    try {
      const r = await fetch(`${API}/api/damages/${id}/status?status=${encodeURIComponent(value)}`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${govToken}` }
      });
      if (r.status === 401) return logout();
      await loadGovernment();
    } catch (_) {
      setLoginMsg("Unable to update complaint status.");
    }
  }

  const mapCenter = useMemo(() => {
    if (rows.length) return [rows[0].latitude, rows[0].longitude];
    return [28.6139, 77.2090];
  }, [rows]);

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <div className="eyebrow">{ui("eyebrow")}</div>
          <h1>Road Intelligence</h1>
          <p>{ui("tagline")}</p>
        </div>
        <div className="top-actions">
          <span className="live">{ui("online")}</span>
          {isGov && <button className="logout-btn" onClick={logout}>Logout</button>}
        </div>
      </header>

      <div className="mode-switch">
        <button className={view === "citizen" ? "active-mode" : ""} onClick={() => setView("citizen")}>{ui("citizenReport")}</button>
        <button className={view === "government" ? "active-mode" : ""} onClick={() => isGov ? setView("government") : setLoginOpen(true)}>{ui("governmentDashboard")} {isGov ? "" : "🔒"}</button>
      </div>

      {view === "citizen" && (
        <main>
          <section className="hero-grid">
            <div className="panel hero-copy">
              <span className="pill">{t("citizenReporting")}</span>
              <h2>{t("heroTitle")}</h2>
              <p>{t("heroDescription")}</p>
              <div className="steps">
                <div><b>01</b><span>{t("step1")}</span></div>
                <div><b>02</b><span>{t("step2")}</span></div>
                <div><b>03</b><span>{t("step3")}</span></div>
                <div><b>04</b><span>{t("step4")}</span></div>
              </div>
            </div>

            <section className="panel citizen-panel">
              <div className="section-title"><div><span className="eyebrow">{t("newComplaint")}</span><h2>{t("reportRoadDamage")}</h2></div><div className="citizen-tools"><LanguagePicker selected={citizenLanguage} query={languageQuery} onQueryChange={setLanguageQuery} onSelect={setCitizenLanguage} filterLabel={t("filterLanguages")} emptyLabel={t("noLanguages")} /><span className="secure-chip">{t("gpsAi")}</span></div></div>
              <p className="muted">{t("locationAttached")}</p>

              <div className="report-mode-switch" role="tablist" aria-label="Complaint submission mode">
                <button type="button" className={citizenMode === "live" ? "selected" : ""} onClick={() => setCitizenMode("live")}>📍 Live complaint</button>
                <button type="button" className={citizenMode === "offline" ? "selected" : ""} onClick={() => setCitizenMode("offline")}>📴 Save offline</button>
              </div>
              <p className="mode-description">{citizenMode === "live" ? "Register now with automatic GPS tracking." : "Save the image and road address on this device. Sync it later from a network area."}</p>

              <div className="camera-area">
                <label className="camera-button">
                  <span className="camera-icon">📷</span>
                  <span><strong>{t("takePhoto")}</strong><small>{t("cameraHint")}</small></span>
                  <input type="file" accept="image/*" capture="environment" onChange={handleFile} />
                </label>
                <label className="gallery-button">{t("gallery")}<input type="file" accept="image/*" onChange={handleFile} /></label>
              </div>

              {preview && <div className="preview-box"><img src={preview} alt="Road preview" /></div>}

              {citizenMode === "live" && <div className="location-box">
                <div className="location-head"><strong>{t("currentLocation")}</strong><button type="button" onClick={getLocation}>{t("refreshGps")}</button></div>
                <p className={latitude !== null ? "location-ok" : ""}>{locationStatus}</p>
                {latitude !== null && <small>{t("coordinatesSent")}</small>}
              </div>}

              <label className="manual-address-field">
                <span>Road address <small>{citizenMode === "offline" ? "required for saved reports" : "optional when GPS lookup is available"}</small></span>
                <textarea value={manualAddress} onChange={e => setManualAddress(e.target.value)} placeholder="Road name, landmark, area and city" rows="2" />
              </label>

              <button className="submit-button" onClick={detect} disabled={busy}>{busy ? t("analyzing") : citizenMode === "live" ? t("submit") : "💾 SAVE REPORT ON THIS DEVICE"}</button>
              {offlineReports.length > 0 && <div className="offline-queue"><div><strong>{offlineReports.length} saved report{offlineReports.length === 1 ? "" : "s"} waiting</strong><small>Sync when you have network access and GPS.</small></div><button type="button" onClick={syncOfflineReports} disabled={busy}>☁️ Sync now</button></div>}
              {msg && <div className="msg">{msg}</div>}
            </section>
          </section>

          {result && (
            <section className="panel result-panel">
              <div className="result-head"><div><span className="pill success">{t("complaintRegistered")}</span><h2>{t("reportReceived")}</h2></div><strong className="complaint-id">#{complaintId ?? (result.count > 0 ? "AUTO-GENERATED" : "NOT REGISTERED")}</strong></div>
              <div className="result-grid">
                <img src={`${API}${result.image_url}`} alt="AI annotated result" className="result-image" />
                <div className="result-details">
                  <div className="detail-card"><span>{t("detectedDamage")}</span><strong>{result.detections.length ? result.detections.map(x => damageLabels[x.damage_type] || x.damage_type).join(", ") : t("noDamage")}</strong></div>
                  <div className="detail-card"><span>{t("locationAddress")}</span><strong>{result.address}</strong></div>
                  <div className="detail-card"><span>{t("gpsCoordinates")}</span><strong>{result.latitude.toFixed(6)}, {result.longitude.toFixed(6)}</strong></div>
                  {result.detections.map((d, i) => <div className="detection-line" key={i}><b>{damageLabels[d.damage_type] || d.damage_type}</b><span>{(d.confidence * 100).toFixed(0)}% confidence</span><em className={d.severity.toLowerCase()}>{d.severity}</em></div>)}
                </div>
              </div>
            </section>
          )}

          <section className="info-strip"><div>🔎 <b>{t("whatNext")}</b></div><p>{t("nextDescription")}</p></section>
        </main>
      )}

      {view === "government" && isGov && (
        <main>
          <div className="gov-heading"><div><span className="eyebrow">AUTHORIZED GOVERNMENT PORTAL</span><h2>Road Maintenance Command Center</h2><p>Review citizen reports, verify locations and track repair progress.</p></div><div className="officer-chip">🔐 Government session active<br/><small>{username}</small></div></div>

          <div className="cards">
            <Card t="Total Issues" v={stats.total || 0} />
            <Card t="Critical" v={stats.critical || 0} c="critical" />
            <Card t="High" v={stats.high || 0} c="high" />
            <Card t="Medium" v={stats.medium || 0} c="medium" />
            <Card t="Pending Verification" v={stats.pending || 0} />
          </div>

          <section className="panel map-panel">
            <div className="section-title"><div><span className="eyebrow">GIS VERIFICATION</span><h2>🛰️ Damage Location & Satellite Verification</h2></div><span className="secure-chip">🔒 OFFICER ONLY</span></div>
            <p className="muted">Use the layer control to switch between street mapping and satellite imagery. Click a marker to inspect the complaint.</p>
            <MapContainer center={mapCenter} zoom={rows.length ? 15 : 10} className="map" key={`${mapCenter[0]}-${mapCenter[1]}`}>
              <LayersControl position="topright">
                <LayersControl.BaseLayer checked name="🗺️ Street Map"><TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" /></LayersControl.BaseLayer>
                <LayersControl.BaseLayer name="🛰️ Satellite View"><TileLayer attribution="Tiles &copy; Esri" url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" /></LayersControl.BaseLayer>
              </LayersControl>
              {rows.map(r => <Marker key={r.id} position={[r.latitude, r.longitude]}><Popup><strong>Complaint #{r.id}</strong><br/>{r.damage_type.toUpperCase()} • {r.severity}<br/>Reports: {r.report_count || 1}<br/>Latest: {formatComplaintDate(r.latest_reported_at || r.detected_at)}<br/>Confidence: {(r.confidence * 100).toFixed(0)}%<br/>{r.address}<br/><small>{r.latitude.toFixed(6)}, {r.longitude.toFixed(6)}</small></Popup></Marker>)}
            </MapContainer>
          </section>

          <section className="panel">
            <div className="section-title"><div><span className="eyebrow">CASE MANAGEMENT</span><h2>🚨 Road Damage Complaints</h2></div><span className="muted">{rows.length} records</span></div>
            <div className="table"><table><thead><tr><th>ID</th><th>Damage</th><th>Reports</th><th>Latest Report</th><th>Confidence</th><th>Severity</th><th>Road Address</th><th>GPS</th><th>Status</th></tr></thead><tbody>{rows.map(r => { const reportCount = r.report_count || 1; const reportedAt = formatComplaintDateParts(r.latest_reported_at || r.detected_at); return <tr key={r.id}><td><b>#{r.id}</b></td><td><strong>{r.damage_type}</strong></td><td><div className={`report-count ${reportCount > 1 ? "report-count-linked" : ""}`}><b>{reportCount}</b><span>{reportCount === 1 ? "report" : "reports"}</span></div>{reportCount > 1 && <small className="linked-note">linked reports</small>}</td><td><div className="latest-report"><b>{reportedAt.date}</b><span>{reportedAt.time}</span></div></td><td>{(r.confidence * 100).toFixed(0)}%</td><td><span className={`badge ${r.severity.toLowerCase()}`}>{r.severity}</span></td><td className="address-cell">{r.address || "Address unavailable"}</td><td className="gps-cell">{r.latitude.toFixed(5)}<br/>{r.longitude.toFixed(5)}</td><td><select value={r.status} onChange={e => status(r.id, e.target.value)}><option>Pending</option><option>Verified</option><option>Rejected</option><option>Assigned</option><option>In Progress</option><option>Repaired</option></select></td></tr>; })}</tbody></table></div>
          </section>
        </main>
      )}

      {loginOpen && (
        <div className="modal-backdrop" onMouseDown={() => setLoginOpen(false)}>
          <div className="login-card" onMouseDown={e => e.stopPropagation()}>
            <button className="close" onClick={() => setLoginOpen(false)}>×</button>
            <div className="login-icon">🏛️</div>
            <span className="eyebrow">RESTRICTED ACCESS</span>
            <h2>Government Officer Login</h2>
            <p>Only authorized government users can access complaints, maps and repair controls.</p>
            <form onSubmit={governmentLogin}>
              <label>Officer ID<input value={username} onChange={e => setUsername(e.target.value)} autoComplete="username" /></label>
              <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" placeholder="Enter password" /></label>
              <button type="submit" className="login-button">🔐 Secure Sign In</button>
            </form>
            {loginMsg && <div className="error-msg">{loginMsg}</div>}
            <div className="demo-note"><b>SIH demo credentials</b><br/>Officer ID: <code>gov_admin</code><br/>Password: <code>SIH@2026</code></div>
          </div>
        </div>
      )}
    </div>
  );
}

function Card({ t, v, c = "" }) { return <div className={`card ${c}`}><span>{t}</span><strong>{v}</strong></div>; }

function LanguagePicker({ selected, query, onQueryChange, onSelect, filterLabel, emptyLabel }) {
  const filteredLanguages = CITIZEN_LANGUAGES.filter(language => language.toLowerCase().includes(query.toLowerCase()));

  return (
    <details className="language-picker">
      <summary><span aria-hidden="true">文</span>{selected}</summary>
      <div className="language-menu">
        <input aria-label={filterLabel} value={query} onChange={e => onQueryChange(e.target.value)} placeholder={filterLabel} />
        <div className="language-options">
          {filteredLanguages.length ? filteredLanguages.map(language => (
            <button type="button" className={language === selected ? "selected-language" : ""} key={language} onClick={e => { onSelect(language); e.currentTarget.closest("details").open = false; }}>
              {language}
            </button>
          )) : <span className="no-languages">{emptyLabel}</span>}
        </div>
      </div>
    </details>
  );
}

createRoot(document.getElementById("root")).render(<App />);
