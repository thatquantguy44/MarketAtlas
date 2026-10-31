// Create a blank query named fnLoadPack; paste this complete function.
// pPackFolder must name ONE immutable pack directory for the entire refresh.
(packFolder as text) as record =>
let
    Root = Text.TrimEnd(packFolder, {"/", "\\"}) & "/",
    Manifest = Json.Document(File.Contents(Root & "manifest.json")),
    Definitions = if Manifest[contract] = "marketatlas-powerbi-pack-v1"
        then Manifest[tables] else error "Unsupported MarketAtlas pack contract",
    TypeMap = [text = type text, integer = Int64.Type, number = type number,
               date = type date, datetimezone = type datetimezone, logical = type logical],
    LoadTable = (name as text) as table =>
        let
            Definition = Record.Field(Definitions, name),
            FileName = if Definition[file] = name & ".csv" then Definition[file]
                       else error "Unexpected table filename",
            Csv = Csv.Document(File.Contents(Root & FileName),
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
            Headers = Table.PromoteHeaders(Csv, [PromoteAllScalars = true]),
            Expected = List.Transform(Definition[columns], each _[name]),
            Checked = if Table.ColumnNames(Headers) = Expected then Headers
                      else error "CSV schema differs from pack manifest",
            Nulls = Table.ReplaceValue(Checked, "", null, Replacer.ReplaceValue, Expected),
            Types = List.Transform(Definition[columns],
                each {_[name], Record.Field(TypeMap, _[type])}),
            Typed = Table.TransformColumnTypes(Nulls, Types, "en-US"),
            Complete = if Table.RowCount(Typed) = Definition[rows] then Typed
                       else error "CSV row count differs from pack manifest"
        in Complete,
    Names = Record.FieldNames(Definitions),
    Result = Record.FromList(List.Transform(Names, each LoadTable(_)), Names)
in
    Result
