/**
 * Turn one of Casebench's published JSON Schemas into the rows of its reference tables.
 *
 * The schemas are generated from the data model, so the tables built from them change when the model does.
 */

export interface JsonSchema {
	$ref?: string;
	$defs?: Record<string, JsonSchema>;
	title?: string;
	description?: string;
	type?: string | string[];
	properties?: Record<string, JsonSchema>;
	required?: string[];
	items?: JsonSchema;
	anyOf?: JsonSchema[];
	oneOf?: JsonSchema[];
	enum?: unknown[];
	const?: unknown;
	format?: string;
	pattern?: string;
	default?: unknown;
	additionalProperties?: boolean | JsonSchema;
}

export interface Field {
	name: string;
	type: string;
	/** The definitions the type names, so a table can link to them. */
	refs: string[];
	required: boolean;
	description?: string;
	default?: string;
	values?: string[];
}

export interface Shape {
	/** `null` for the document's own top level. */
	name: string | null;
	description?: string;
	fields: Field[];
	values?: string[];
}

const definition = (ref: string) => ref.replace('#/$defs/', '');

interface Rendered {
	type: string;
	refs: string[];
}

/** A short, readable type: `string`, `Fact[]`, `map of integer`, `string | null`. */
export function typeOf(schema: JsonSchema): Rendered {
	if (schema.$ref) {
		const name = definition(schema.$ref);
		return { type: name, refs: [name] };
	}
	const union = schema.anyOf ?? schema.oneOf;
	if (union) {
		const parts = union.map(typeOf);
		return { type: parts.map((p) => p.type).join(' | '), refs: parts.flatMap((p) => p.refs) };
	}
	if (schema.const !== undefined) return { type: JSON.stringify(schema.const), refs: [] };
	if (schema.enum) return { type: schema.enum.map((v) => JSON.stringify(v)).join(' | '), refs: [] };

	const type = Array.isArray(schema.type) ? schema.type.join(' | ') : schema.type;
	if (type === 'array') {
		const item = schema.items ? typeOf(schema.items) : { type: 'any', refs: [] };
		const wrapped = item.type.includes(' | ') ? `(${item.type})` : item.type;
		return { type: `${wrapped}[]`, refs: item.refs };
	}
	if (type === 'object' && !schema.properties) {
		const values = schema.additionalProperties;
		if (values && typeof values === 'object') {
			const inner = typeOf(values);
			return { type: `map of ${inner.type}`, refs: inner.refs };
		}
		return { type: 'object', refs: [] };
	}
	if (type === 'string' && schema.format) return { type: `string (${schema.format})`, refs: [] };
	return { type: type ?? 'any', refs: [] };
}

function fields(schema: JsonSchema): Field[] {
	const required = new Set(schema.required ?? []);
	return Object.entries(schema.properties ?? {}).map(([name, property]) => {
		const { type, refs } = typeOf(property);
		return {
			name,
			type,
			refs,
			required: required.has(name),
			description: property.description,
			default: property.default === undefined ? undefined : JSON.stringify(property.default),
			values: property.pattern ? [`matches ${property.pattern}`] : undefined,
		};
	});
}

/** The top level first, then every definition it reaches, in the order a reader meets them. */
export function shapes(schema: JsonSchema): Shape[] {
	const defs = schema.$defs ?? {};
	const seen = new Set<string>();
	const ordered: Shape[] = [{ name: null, description: schema.description, fields: fields(schema) }];

	const visit = (names: string[]) => {
		for (const name of names) {
			if (seen.has(name) || !defs[name]) continue;
			seen.add(name);
			const def = defs[name];
			const own = fields(def);
			ordered.push({
				name,
				description: def.description,
				fields: own,
				values: def.enum?.map((v) => String(v)),
			});
			visit(own.flatMap((f) => f.refs));
		}
	};
	visit(ordered[0]!.fields.flatMap((f) => f.refs));
	return ordered;
}
