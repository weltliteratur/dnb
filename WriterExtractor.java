package de.l3s.wikidata.extractor;

import java.io.BufferedReader;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.wikidata.wdtk.datamodel.interfaces.EntityDocumentProcessor;
import org.wikidata.wdtk.datamodel.interfaces.EntityIdValue;
import org.wikidata.wdtk.datamodel.interfaces.ItemDocument;
import org.wikidata.wdtk.datamodel.interfaces.ItemIdValue;
import org.wikidata.wdtk.datamodel.interfaces.MonolingualTextValue;
import org.wikidata.wdtk.datamodel.interfaces.PropertyDocument;
import org.wikidata.wdtk.datamodel.interfaces.Statement;
import org.wikidata.wdtk.datamodel.interfaces.Value;
import org.wikidata.wdtk.datamodel.json.jackson.datavalues.JacksonValueString;

import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.JsonGenerator;

/**
 * Reads all subclasses (P279) of writer (Q36180) from a file and then iterates
 * over the Wikidata dataset to find all items which have a GND id (P227) and an
 * occupation (P106) of one of the subclasses.
 * 
 * @author rja
 *
 */
public class WriterExtractor implements EntityDocumentProcessor {

	private final Map<String, String> subclasses;
	private final JsonGenerator json;

	// matches <http://www.wikidata.org/entity/Q36180>
	private static final Pattern WD_ID_PATTERN = Pattern.compile("^<.+/(Q[0-9]+)>$"); 
	// matches "writer"@en
	private static final Pattern WD_LABEL_PATTERN = Pattern.compile("^\"(.+)\"@en$");
	
	/**
	 * For the given Wikidata id, read all subclasses (P279) of that class.
	 * 
	 * @param item
	 * @throws IOException 
	 */
	public static Map<String, String> getSubclasses(final String fileName) throws IOException {
		final BufferedReader buf = new BufferedReader(new InputStreamReader(new FileInputStream(fileName), "utf-8"));
		final Map<String, String> subclasses = new HashMap<String, String>();
		String line;
		while ((line = buf.readLine()) != null) {
			/*
			 * input file format:
			 * ?subclass       ?subclassLabel
			 * <http://www.wikidata.org/entity/Q36180> "writer"@en
			 * <http://www.wikidata.org/entity/Q28389> "screenwriter"@en
			 * <http://www.wikidata.org/entity/Q49757> "poet"@en
			 * 
			 */
			if (line.startsWith("<")) {
				final String[] parts = line.trim().split("\t");
				final Matcher me = WD_ID_PATTERN.matcher(parts[0]);
				if (me.matches()) {
					final String id = me.group(1);
					final Matcher ml = WD_LABEL_PATTERN.matcher(parts[1]);
					final String label;
					if (ml.matches()) {
						label = ml.group(1);
					} else {
						label = id;
					}
					subclasses.put(id, label);
				}
			}
		}
		buf.close();
		return subclasses;
	}

	public static void main(String[] args) throws IOException {
		ExampleHelpers.configureLogging();

		final String subclasses = "/home/rja/work/weighing/wikidata_writer_subclasses.tsv";

		final WriterExtractor writerExtractor = new WriterExtractor(subclasses, "gndwriter.json");
		ExampleHelpers.processEntitiesFromWikidataDump(writerExtractor);
		writerExtractor.finish();
	}


	public void finish() throws IOException {
		this.json.writeEndObject();
		this.json.close();
	}

	public WriterExtractor(final String subclassesFile, final String outputFile) throws IOException {
		this.subclasses = getSubclasses(subclassesFile);
		final JsonFactory factory = new JsonFactory();
		this.json = factory.createGenerator(new OutputStreamWriter(new FileOutputStream(outputFile), "utf-8"));
		this.json.writeStartObject();
	}

	/**
	 * For a document that has the occupation (P106) property, checks all values
	 * against this.subclasses. All found matches are returned.
	 * 
	 * @param itemDocument
	 * @return
	 */
	private Set<String> getWriterOccupations(final ItemDocument itemDocument) {
		final Set<String> writerOccupations = new HashSet<String>();
		// extract occupations - since an item can have several values, we retrieve the statement group
		for (final Statement statement : itemDocument.findStatementGroup("P106").getStatements()) {
			final String occup = getValue(statement.getValue());
			if (this.subclasses.containsKey(occup)) {
				writerOccupations.add(occup);
			}
		}
		return writerOccupations;
	}

	public void processItemDocument(final ItemDocument itemDocument) {
		/*
		 * check for occupation (P106) and GND id (P227) properties
		 */
		//if (itemDocument.hasStatementValue("P31", Datamodel.makeWikidataItemIdValue("Q5"))) {
		if (itemDocument.hasStatement("P106") && itemDocument.hasStatement("P227")) {
			// extract label
			final ItemIdValue itemId = itemDocument.getItemId();
			final MonolingualTextValue label = itemDocument.getLabels().get("en");
			// ignore items without label
			if (label != null) {
				final Set<String> occupations = getWriterOccupations(itemDocument);
				if (!occupations.isEmpty()) {
					/*
					 * an item can have several GND ids (example: https://www.wikidata.org/wiki/Q19004)
					 * - get and print them all 
					 */
					for (final Statement statement : itemDocument.findStatementGroup("P227")) {
						final String gndid = getValue(statement.getValue());
						try {
							// write JSON
							json.writeFieldName(gndid);         // "118540238" : 
							json.writeStartObject();            // {
							json.writeFieldName("id");          //   "id" :
							json.writeString(itemId.getId());   //          "Q5879",
							json.writeFieldName("name");        //   "name" :
							json.writeString(label.getText());  //            "Johann Wolfgang von Goethe",
							json.writeFieldName("occupations"); //   "occupations" : 
							json.writeStartArray();             //     [
							for (final String occupation : occupations) {
								json.writeStartObject();        //        {
								json.writeFieldName("id");      //          "id" :
								json.writeString(occupation);   //                 "Q1209498",
								json.writeFieldName("name");    //          "name" : 
								json.writeString(this.subclasses.get(occupation)); // "poet lawyer"
								json.writeEndObject();          //        }
							}
							json.writeEndArray();               //     ]
							json.writeEndObject();              // }
							json.writeRaw('\n');                // add linebreak
							
						} catch (final Exception e) {
							System.err.println("error for " + itemId + "(" + label + ")");
							e.printStackTrace();
						}
					}
				} 
			}
		}
	}

	private String getValue(final Value val) {
		if (val instanceof EntityIdValue) {
			return ((EntityIdValue)val).getId();
		}
		if (val instanceof JacksonValueString) {
			return ((JacksonValueString)val).getString();
		}
		return null;
	}

	public void processPropertyDocument(PropertyDocument arg0) {
		// TODO Auto-generated method stub

	}

}
