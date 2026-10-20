/*
  Magic Word — Spacebrew word counter

  Registers as a Spacebrew 2.0 client (subscriber only) and listens for
  incoming string messages on its "word" subscriber. Every distinct word
  received is added to the screen with a running count of how many times
  it's been said.

  Pairs with the "Magic Word" Ritual (../../../08-test-experiences.md),
  which publishes matched keywords from AudioObserver transcripts as
  Spacebrew client "MagicWordRitual", publisher "word:string". Session
  start wires the route MagicWordRitual/word -> MagicWordCounter/word.

  Library required: MQTT (by Joel Gaehwiler) — Sketch > Import Library >
  Add Library...
*/

import mqtt.*;

MQTTClient client;

String broker = "mqtt://localhost";
String clientName = "MagicWordCounter";
String description = "Magic Word counter";
String[] subscribers = { "word:string" };

IntDict counts = new IntDict();
boolean connected = false;

String lastWord = "";
int lastWordAt = -10000; // millis() timestamp of the most recent message, for a brief highlight

color bg = color(18, 18, 22);
color textColor = color(235, 235, 240);
color dimColor = color(120, 120, 130);
color highlightColor = color(255, 210, 90);

PFont titleFont, listFont;

void setup() {
  size(600, 600);
  titleFont = createFont("Helvetica-Bold", 28);
  listFont = createFont("Helvetica", 24);

  client = new MQTTClient(this);
  // Last Will: if this sketch closes uncleanly, the broker announces our
  // departure so the router can deregister us.
  client.setWill("YuxiSpace/leave", clientName);
  client.connect(broker, clientName);
}

void draw() {
  background(bg);

  textFont(titleFont);
  textAlign(LEFT, TOP);
  fill(textColor);
  text("Magic Word", 30, 30);

  textFont(listFont);
  textSize(14);
  fill(connected ? dimColor : color(200, 90, 90));
  text(connected ? "listening..." : "connecting...", 32, 72);

  drawCounts();
}

void drawCounts() {
  if (counts.size() == 0) {
    fill(dimColor);
    textSize(18);
    text("no words heard yet", 32, 120);
    return;
  }

  counts.sortValuesReverse();

  int y = 120;
  int rowHeight = 42;
  for (int i = 0; i < counts.size(); i++) {
    if (y > height - 30) break; // don't run off the bottom of the canvas

    String word = counts.key(i);
    int count = counts.value(i);
    boolean isRecent = word.equals(lastWord) && (millis() - lastWordAt) < 1500;

    fill(isRecent ? highlightColor : textColor);
    textSize(24);
    textAlign(LEFT, TOP);
    text(word, 40, y);

    textAlign(RIGHT, TOP);
    text(count, height - 40, y);

    y += rowHeight;
  }
}

void clientConnected() {
  connected = true;
  println("Connected to Spacebrew broker");

  String subsStr = join(subscribers, ", ");
  String regMsg = clientName + ", " + description + ", pubs(), subs(" + subsStr + ")";
  client.publish("YuxiSpace", regMsg);

  for (String sub : subscribers) {
    String subName = split(sub, ':')[0];
    client.subscribe(clientName + "/" + subName);
  }
}

void messageReceived(String topic, byte[] payload) {
  String word = trim(new String(payload)).toLowerCase();
  if (word.length() == 0) return;
  if (!topic.equals(clientName + "/word")) return;

  counts.increment(word);
  lastWord = word;
  lastWordAt = millis();
}

void connectionLost() {
  connected = false;
  println("Connection to Spacebrew lost");
}
